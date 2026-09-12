from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import crud
import models
import schemas
from database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Student Task Scheduler API",
    description="A conflict-aware task and revision scheduler for students.",
    version="1.0.0",
)

# Allow the Streamlit frontend (or anything) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def root():
    return {"message": "Task Scheduler API is running"}


@app.get("/categories", tags=["tasks"])
def read_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


@app.post("/tasks", response_model=schemas.TaskOut, tags=["tasks"])
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(db, task)


@app.get("/tasks", response_model=List[schemas.TaskOut], tags=["tasks"])
def read_tasks(category: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_tasks(db, category)


@app.get("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@app.put("/tasks/{task_id}", response_model=schemas.TaskOut, tags=["tasks"])
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = crud.update_task(db, task_id, task)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@app.delete("/tasks/{task_id}", tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.delete_task(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}


@app.get("/tasks/conflicts/check", tags=["conflicts"])
def check_conflicts(db: Session = Depends(get_db)):
    return crud.sync_and_get_conflicts(db)