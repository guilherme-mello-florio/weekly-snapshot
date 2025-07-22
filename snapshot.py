import os
from datetime import date, timedelta
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Make sure your minimal models.py includes all of these
from models import (
    Project, ProjectInterfaceStatus, WeeklyProgressSnapshot,
    ProjectScheduleTask, UploadHistory, InterfaceStatusEnum
)

# --- CONFIGURATION ---
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def take_weekly_snapshots():
    db = SessionLocal()
    try:
        today = date.today()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)

        print(f"Running weekly snapshot for the week ending on: {last_sunday}")

        projects = db.query(Project).all()
        if not projects:
            print("No projects found to snapshot.")
            return

        for project in projects:
            print(f"Processing project: {project.project_name}...")

            # --- 1. Fetch all data for the project ---
            all_statuses = db.query(ProjectInterfaceStatus).filter(ProjectInterfaceStatus.project_id == project.id).all()
            all_tasks = db.query(ProjectScheduleTask).filter(ProjectScheduleTask.project_id == project.id).all()
            
            subquery = db.query(
                UploadHistory.interface_name,
                func.max(UploadHistory.uploaded_at).label('max_uploaded_at')
            ).filter(UploadHistory.project_name == project.project_name).group_by(UploadHistory.interface_name).subquery()
            
            latest_uploads = db.query(UploadHistory).join(
                subquery,
                and_(
                    UploadHistory.interface_name == subquery.c.interface_name,
                    UploadHistory.uploaded_at == subquery.c.max_uploaded_at
                )
            ).all()
            latest_upload_map = {u.interface_name: u.status for u in latest_uploads}

            total_interfaces = len(all_statuses)
            if total_interfaces == 0:
                print(f"Project {project.project_name} has no interfaces to snapshot.")
                continue

            # --- 2. Determine the precise status of each interface ---
            TASK_ORDER = {"Data Extraction": 1, "Data Delivery": 2, "Technical Validation": 3, "Functional Validation": 4}
            tasks_by_interface = {}
            for task in all_tasks:
                if task.interface_name not in tasks_by_interface:
                    tasks_by_interface[task.interface_name] = []
                tasks_by_interface[task.interface_name].append(task)

            counts = {"Completed": 0, "In Progress": 0, "Failed": 0, "Delayed": 0, "Not Started": 0}
            for s in all_statuses:
                tasks = tasks_by_interface.get(s.interface_name, [])
                sorted_tasks = sorted(tasks, key=lambda t: TASK_ORDER.get(t.task_name, 99))
                
                all_tasks_completed = all(task.status == 'Concluído' for task in sorted_tasks) and sorted_tasks
                first_pending_task = next((task for task in sorted_tasks if task.status != 'Concluído'), None)

                status_category = "Not Started" # Default
                if all_tasks_completed:
                    status_category = "Completed"
                elif latest_upload_map.get(s.interface_name) == "Error":
                    status_category = "Failed"
                elif first_pending_task and first_pending_task.end_date and first_pending_task.end_date < today:
                    status_category = "Delayed"
                elif s.status == InterfaceStatusEnum.in_progress.value or s.status.startswith("Completed"):
                    status_category = "In Progress"
                
                counts[status_category] += 1

            # --- 3. Save the snapshot ---
            snapshot = db.query(WeeklyProgressSnapshot).filter(
                WeeklyProgressSnapshot.project_id == project.id,
                WeeklyProgressSnapshot.week_end_date == last_sunday
            ).first()

            if snapshot:
                print("Updating existing snapshot...")
                snapshot.completed_count = counts["Completed"]
                snapshot.in_progress_count = counts["In Progress"]
                snapshot.failed_count = counts["Failed"]
                snapshot.delayed_count = counts["Delayed"]
                snapshot.not_started_count = counts["Not Started"]
                snapshot.total_interfaces = total_interfaces
            else:
                print("Creating new snapshot...")
                snapshot = WeeklyProgressSnapshot(
                    project_id=project.id,
                    week_end_date=last_sunday,
                    completed_count=counts["Completed"],
                    in_progress_count=counts["In Progress"],
                    failed_count=counts["Failed"],
                    delayed_count=counts["Delayed"],
                    not_started_count=counts["Not Started"],
                    total_interfaces=total_interfaces
                )
                db.add(snapshot)
            
            db.commit()
            print(f"Successfully saved snapshot for project {project.project_name}.")

    except Exception as e:
        print(f"An error occurred during the snapshot process: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("--- Starting Weekly Progress Snapshot Job ---")
    take_weekly_snapshots()
    print("--- Weekly Progress Snapshot Job Finished ---")
