from typing import Optional

from sqlalchemy.orm import Session

import models
import schemas


def get_tasks(db: Session, category: Optional[str] = None):
    query = db.query(models.Task)
    if category:
        query = query.filter(models.Task.category == category)
    return query.order_by(models.Task.due_date).all()


def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def create_task(db: Session, task: schemas.TaskCreate):
    db_task = models.Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task(db: Session, task_id: int, task: schemas.TaskUpdate):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    for key, value in task.dict(exclude_unset=True).items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    db_task = get_task(db, task_id)
    if not db_task:
        return None
    db.delete(db_task)
    db.commit()
    return db_task


def get_conflicts(db: Session):
    """
    Two tasks 'conflict' if they are both high-priority, still pending,
    and their [start_date, due_date] windows overlap.
    """
    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.priority == models.PriorityEnum.high,
            models.Task.status == models.StatusEnum.pending,
        )
        .order_by(models.Task.start_date)
        .all()
    )

    conflicts = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            t1, t2 = tasks[i], tasks[j]
            overlap = t1.start_date <= t2.due_date and t2.start_date <= t1.due_date
            if overlap:
                conflicts.append(
                    {
                        "task_1": t1.title,
                        "task_2": t2.title,
                        "overlap_start": max(t1.start_date, t2.start_date).isoformat(),
                        "overlap_end": min(t1.due_date, t2.due_date).isoformat(),
                    }
                )
    return conflicts
