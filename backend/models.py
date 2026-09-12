import enum

from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class PriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class StatusEnum(str, enum.Enum):
    pending = "pending"
    done = "done"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, default="General", nullable=False)
    subject = Column(String, nullable=True)

    start_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    priority = Column(
        Enum(PriorityEnum),
        default=PriorityEnum.medium,
        nullable=False
    )

    status = Column(
        Enum(StatusEnum),
        default=StatusEnum.pending,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConflictLog(Base):
    __tablename__ = "conflict_log"

    __table_args__ = (
        UniqueConstraint(
            "task_1_id",
            "task_2_id",
            name="uq_conflict_pair"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    task_1_id = Column(Integer, nullable=False)
    task_2_id = Column(Integer, nullable=False)

    task_1_title = Column(String, nullable=False)
    task_2_title = Column(String, nullable=False)

    overlap_start = Column(Date, nullable=False)
    overlap_end = Column(Date, nullable=False)

    status = Column(String, default="active", nullable=False)

    first_detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    resolved_at = Column(DateTime(timezone=True), nullable=True)

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True
    )