# models.py (Minimal version for snapshot cron job)

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Date,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

# Base class for all models
# You would typically import this from your database.py, but defining it here works for a standalone script.
Base = declarative_base()

# Enum needed by ProjectInterfaceStatus
class InterfaceStatusEnum(enum.Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    completed_awaiting_upload = "Completed and awaiting upload in RELEX system"
    completed_and_uploaded = "Completed and uploaded"

# Needed to get the project ID and name
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String(45), unique=True)
    
    # This relationship is needed for SQLAlchemy to understand the link
    weekly_snapshots = relationship("WeeklyProgressSnapshot", back_populates="project")

# Needed to query the status of each interface
class ProjectInterfaceStatus(Base):
    __tablename__ = 'project_interface_status'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    interface_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)

# The model for the table we are writing to
class WeeklyProgressSnapshot(Base):
    __tablename__ = 'weekly_progress_snapshots'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    week_end_date = Column(Date, nullable=False)
    completed_count = Column(Integer, nullable=False, default=0)
    in_progress_count = Column(Integer, nullable=False, default=0)
    not_started_count = Column(Integer, nullable=False, default=0)
    total_interfaces = Column(Integer, nullable=False, default=0)

    # Relationship to the project
    project = relationship("Project", back_populates="weekly_snapshots")

    # Ensure there's only one snapshot per project per week
    __table_args__ = (UniqueConstraint('project_id', 'week_end_date', name='_project_week_snapshot_uc'),)
