from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models import PriorityEnum, CategoryEnum, StatusEnum


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: CategoryEnum = CategoryEnum.general
    subject: Optional[str] = None
    start_date: date
    due_date: date
    priority: PriorityEnum = PriorityEnum.medium
    status: StatusEnum = StatusEnum.pending


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[CategoryEnum] = None
    subject: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[PriorityEnum] = None
    status: Optional[StatusEnum] = None


class TaskOut(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
