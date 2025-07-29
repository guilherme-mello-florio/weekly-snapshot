import os
from datetime import date, timedelta
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Assuming models are in a shared 'models.py' file or defined here
from models import Project, ProjectInterfaceStatus, WeeklyProgressSnapshot, UploadHistory, ProjectScheduleTask, InterfaceStatusEnum

# --- Database Connection ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Scramble_06!@localhost:3306/wysuppdb")
if DATABASE_URL and DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def take_weekly_snapshot():
    db = SessionLocal()
    today = date.today()
    # Ensure snapshot is taken on a specific day, e.g., Sunday
    if today.weekday() != 6: # 6 is Sunday
        print("Not a snapshot day. Exiting.")
        db.close()
        return

    projects = db.query(Project).all()
    for project in projects:
        print(f"Processing snapshot for project: {project.project_name}...")
        
        # --- THIS IS THE NEW, HARMONIZED LOGIC ---
        all_statuses = db.query(ProjectInterfaceStatus).filter(ProjectInterfaceStatus.project_id == project.id).all()
        total_interfaces = len(all_statuses)
        if total_interfaces == 0:
            continue

        all_tasks = db.query(ProjectScheduleTask).filter(ProjectScheduleTask.project_id == project.id).all()
        all_uploads = db.query(UploadHistory).filter(UploadHistory.project_name == project.project_name).order_by(UploadHistory.uploaded_at.asc()).all()

        interface_file_status_map = {}
        for upload in all_uploads:
            if upload.interface_name not in interface_file_status_map:
                interface_file_status_map[upload.interface_name] = {}
            interface_file_status_map[upload.interface_name][upload.filename] = upload.status
        
        interfaces_with_failures = {
            name: "Error" in statuses.values() for name, statuses in interface_file_status_map.items()
        }
        
        tasks_by_interface = {name: [] for name in [s.interface_name for s in all_statuses]}
        for task in all_tasks:
            if task.interface_name in tasks_by_interface:
                tasks_by_interface[task.interface_name].append(task)

        counts = {"Completed": 0, "In Progress": 0, "Failed": 0, "Delayed": 0, "Not Started": 0}
        
        for s in all_statuses:
            tasks = tasks_by_interface.get(s.interface_name, [])
            has_failed_file = interfaces_with_failures.get(s.interface_name, False)
            all_tasks_completed = all(t.status == 'Concluído' for t in tasks) and tasks
            
            first_pending_task = next((t for t in sorted(tasks, key=lambda t: t.id) if t.status != 'Concluído'), None)
            is_delayed = first_pending_task and first_pending_task.end_date and first_pending_task.end_date < today

            if all_tasks_completed:
                counts["Completed"] += 1
            elif has_failed_file:
                counts["Failed"] += 1
            # Note: We don't count delayed as a primary status for the main counts
            elif s.status == InterfaceStatusEnum.not_started.value:
                counts["Not Started"] += 1
            else:
                counts["In Progress"] += 1
            
            if is_delayed and not all_tasks_completed:
                counts["Delayed"] += 1 # We count this separately

        # --- END OF HARMONIZED LOGIC ---

        snapshot = WeeklyProgressSnapshot(
            project_id=project.id,
            week_end_date=today,
            completed_count=counts["Completed"],
            in_progress_count=counts["In Progress"],
            failed_count=counts["Failed"],
            delayed_count=counts["Delayed"],
            not_started_count=counts["Not Started"],
            total_interfaces=total_interfaces
        )

        db.merge(snapshot) # Use merge to insert or update if a snapshot for today already exists
        print(f"Snapshot for {project.project_name} saved.")

    db.commit()
    db.close()
    print("Weekly snapshots completed.")

if __name__ == "__main__":
    take_weekly_snapshot()
