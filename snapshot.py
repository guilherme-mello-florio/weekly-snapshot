# snapshot.py
import os
from datetime import date, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import your models by copying a minimal models.py into the same directory
# It should contain: Project, ProjectInterfaceStatus, WeeklyProgressSnapshot, InterfaceStatusEnum
from models import Project, ProjectInterfaceStatus, WeeklyProgressSnapshot, InterfaceStatusEnum

# --- CONFIGURATION ---
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def take_weekly_snapshots():
    """
    Calculates the status counts for each project and saves them to the snapshot table.
    """
    db = SessionLocal()
    try:
        today = date.today()
        # Find the most recent Sunday. If today is Sunday, it's today.
        # weekday() returns 0 for Monday and 6 for Sunday.
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)

        print(f"Running weekly snapshot for the week ending on: {last_sunday}")

        projects = db.query(Project).all()
        if not projects:
            print("No projects found to snapshot.")
            return

        for project in projects:
            print(f"Processing project: {project.project_name}...")

            # Query all interface statuses for the current project
            statuses = db.query(ProjectInterfaceStatus.status)\
                .filter(ProjectInterfaceStatus.project_id == project.id)\
                .all()
            
            total_interfaces = len(statuses)
            completed_count = 0
            in_progress_count = 0
            not_started_count = 0

            for status_tuple in statuses:
                status = status_tuple[0]
                if status.startswith("Completed"):
                    completed_count += 1
                elif status == InterfaceStatusEnum.in_progress.value:
                    in_progress_count += 1
                elif status == InterfaceStatusEnum.not_started.value:
                    not_started_count += 1
                # Note: "Failed validation" is counted as "in progress" for the KPI
                elif status == "Failed validation":
                     in_progress_count += 1

            # Find if a snapshot for this project and week already exists
            snapshot = db.query(WeeklyProgressSnapshot).filter(
                WeeklyProgressSnapshot.project_id == project.id,
                WeeklyProgressSnapshot.week_end_date == last_sunday
            ).first()

            if snapshot:
                print("Updating existing snapshot...")
                snapshot.completed_count = completed_count
                snapshot.in_progress_count = in_progress_count
                snapshot.not_started_count = not_started_count
                snapshot.total_interfaces = total_interfaces
            else:
                print("Creating new snapshot...")
                snapshot = WeeklyProgressSnapshot(
                    project_id=project.id,
                    week_end_date=last_sunday,
                    completed_count=completed_count,
                    in_progress_count=in_progress_count,
                    not_started_count=not_started_count,
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

