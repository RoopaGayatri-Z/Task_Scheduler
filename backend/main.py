
import os
import time
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import auth
import crud
import models
import schemas
from database import Base, engine, get_db


# Retry table creation in case multiple backend containers start together.
for attempt in range(3):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except Exception as exc:
        print(f"create_all attempt {attempt + 1} failed: {exc}")
        if attempt == 2:
            raise
        time.sleep(1.5)


INSTANCE_NAME = os.getenv("INSTANCE_NAME", "local")


app = FastAPI(
    title="Student Task Scheduler API",
    description="A conflict-aware task and revision scheduler for students.",
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_instance_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Instance"] = INSTANCE_NAME
    return response


# ----------------------------- HEALTH -----------------------------

@app.get("/", tags=["health"])
def root():
    return {
        "message": "Task Scheduler API is running",
        "instance": INSTANCE_NAME
    }


@app.get("/instance", tags=["health"])
def instance():
    return {"instance": INSTANCE_NAME}


# -------------------------- AUTHENTICATION -------------------------

@app.post("/auth/register", response_model=schemas.RegisterOut, tags=["auth"])
def register(body: schemas.UserRegister, db: Session = Depends(get_db)):

    if db.query(models.User).filter(
        models.User.username == body.username
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Username already taken"
        )

    secret = auth.new_totp_secret()

    user = models.User(
        username=body.username,
        password_hash=auth.hash_password(body.password),
        role="student",
        totp_secret=secret,
        totp_enabled=True
    )

    db.add(user)
    db.commit()

    return schemas.RegisterOut(
        username=user.username,
        role=user.role,
        totp_secret=secret,
        otpauth_uri=auth.provisioning_uri(user.username, secret)
    )


@app.post("/auth/login", response_model=schemas.TokenOut, tags=["auth"])
def login(body: schemas.UserLogin, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(
        models.User.username == body.username
    ).first()

    invalid = HTTPException(
        status_code=401,
        detail="Invalid username, password or authenticator code"
    )

    if user is None or not auth.verify_password(
        body.password, user.password_hash
    ):
        raise invalid

    if user.totp_enabled and not auth.verify_totp(
        user.totp_secret, body.totp_code
    ):
        raise invalid

    return schemas.TokenOut(
        access_token=auth.create_access_token(user),
        role=user.role,
        username=user.username
    )


# ----------------------------- TASKS -------------------------------

# Read endpoints: any logged-in user, including viewers.
# Write endpoints: only students and faculty.


# ----------------------------- TASKS -------------------------------

# Read endpoints: any logged-in user, including viewers.
# Write endpoints: only students and faculty.


@app.get("/categories", tags=["tasks"])
def read_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.get_categories(db, current_user.id)


@app.post(
    "/tasks",
    response_model=schemas.TaskOut,
    tags=["tasks"]
)
def create_task(
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(*auth.WRITE_ROLES))
):
    return crud.create_task(db, task, current_user.id)


@app.get(
    "/tasks",
    response_model=List[schemas.TaskOut],
    tags=["tasks"]
)
def read_tasks(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.get_tasks(db, current_user.id, category)


@app.get("/tasks/conflicts/check", tags=["conflicts"])
def check_conflicts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return crud.sync_and_get_conflicts(db, current_user.id)


@app.post(
    "/tasks/conflicts/{conflict_id}/dismiss",
    tags=["conflicts"]
)
def dismiss_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(*auth.WRITE_ROLES))
):
    log_entry = crud.dismiss_conflict(db, conflict_id, current_user.id)

    if not log_entry:
        raise HTTPException(
            status_code=404,
            detail="Conflict not found"
        )

    return {"message": "Conflict acknowledged for 30 minutes"}


@app.get(
    "/tasks/{task_id}",
    response_model=schemas.TaskOut,
    tags=["tasks"]
)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_task = crud.get_task(db, task_id, current_user.id)

    if not db_task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return db_task


@app.put(
    "/tasks/{task_id}",
    response_model=schemas.TaskOut,
    tags=["tasks"]
)
def update_task(
    task_id: int,
    task: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(*auth.WRITE_ROLES))
):
    db_task = crud.update_task(db, task_id, task, current_user.id)

    if not db_task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return db_task


@app.delete("/tasks/{task_id}", tags=["tasks"])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles(*auth.WRITE_ROLES))
):
    db_task = crud.delete_task(db, task_id, current_user.id)

    if not db_task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {"message": "Task deleted"}
