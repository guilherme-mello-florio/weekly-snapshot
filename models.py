# models.py

from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, 
                        Boolean, UniqueConstraint, Date)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class InterfaceStatusEnum(enum.Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    failed = "Failed validation"
    completed_awaiting_upload = "Completed and awaiting upload in RELEX system"
    completed_and_uploaded = "Completed and uploaded"

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(45), unique=True, index=True, nullable=False)
    # Relationships
    interface_statuses = relationship("ProjectInterfaceStatus", back_populates="project")
    schedule_tasks = relationship("ProjectScheduleTask", back_populates="project")
    weekly_snapshots = relationship("WeeklyProgressSnapshot", back_populates="project")

class ProjectInterfaceStatus(Base):
    __tablename__ = 'project_interface_status'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    interface_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default=InterfaceStatusEnum.not_started.value)
    # Relationships
    project = relationship("Project", back_populates="interface_statuses")

class UploadHistory(Base):
    __tablename__ = 'upload_history'
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime)
    status = Column(String(50), nullable=False)
    project_name = Column(String(45), nullable=True)
    interface_name = Column(String(255), nullable=True)

class ProjectScheduleTask(Base):
    __tablename__ = 'project_schedule_tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    interface_name = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default='Pendente')
    # Relationships
    project = relationship("Project", back_populates="schedule_tasks")

class WeeklyProgressSnapshot(Base):
    __tablename__ = 'weekly_progress_snapshots'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    week_end_date = Column(Date, nullable=False)
    
    # --- MODIFIED: All fields are now present ---
    completed_count = Column(Integer, nullable=False, default=0)
    in_progress_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    delayed_count = Column(Integer, nullable=False, default=0)
    not_started_count = Column(Integer, nullable=False, default=0)
    total_interfaces = Column(Integer, nullable=False, default=0)

    # Relationships
    project = relationship("Project", back_populates="weekly_snapshots")
    __table_args__ = (UniqueConstraint('project_id', 'week_end_date', name='_project_week_snapshot_uc'),)
