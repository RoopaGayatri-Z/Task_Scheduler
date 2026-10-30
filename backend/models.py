import enum

from sqlalchemy import Boolean, Column, Integer, String, Date, DateTime, Enum, UniqueConstraint, ForeignKey
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
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

class User(Base):
    """
    Application account. Passwords are stored ONLY as salted bcrypt hashes,
    never as plain text. totp_secret is the shared secret for the
    authenticator app (Google/Microsoft Authenticator).
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="student", nullable=False)  # student | faculty | viewer
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
