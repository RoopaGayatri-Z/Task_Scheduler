
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from models import PriorityEnum, StatusEnum


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str = "General"
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
    category: Optional[str] = None
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


# -------------------- Authentication schemas --------------------

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    # bcrypt only uses the first 72 bytes
    password: str = Field(min_length=8, max_length=64)


class UserLogin(BaseModel):
    username: str
    password: str
    totp_code: str = Field(min_length=6, max_length=6)


class RegisterOut(BaseModel):
    username: str
    role: str
    totp_secret: str
    otpauth_uri: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
