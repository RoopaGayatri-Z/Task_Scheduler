from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

import models
import schemas


def get_categories(db: Session):
    rows = db.query(models.Task.category).distinct().all()
    return sorted({r[0] for r in rows if r[0]})


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


def sync_and_get_conflicts(db: Session):
    """
    Recomputes currently-overlapping high-priority, pending task pairs, logs them,
    and flips any previously-active pair to 'resolved' once it no longer overlaps
    (e.g. because the user rescheduled one of the tasks, changed its priority,
    marked it done, or deleted it).
    """
    tasks = (
        db.query(models.Task)
        .filter(
            models.Task.priority == models.PriorityEnum.high,
            models.Task.status == models.StatusEnum.pending,
        )
        .order_by(models.Task.id)
        .all()
    )

    # key = (lower_task_id, higher_task_id) -> (lo_task, hi_task, overlap_start, overlap_end)
    active_pairs = {}
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            t1, t2 = tasks[i], tasks[j]
            overlap = t1.start_date <= t2.due_date and t2.start_date <= t1.due_date
            if overlap:
                lo, hi = (t1, t2) if t1.id < t2.id else (t2, t1)
                active_pairs[(lo.id, hi.id)] = (
                    lo,
                    hi,
                    max(t1.start_date, t2.start_date),
                    min(t1.due_date, t2.due_date),
                )

    # upsert currently-active pairs into the log
    for (lo_id, hi_id), (lo, hi, ov_start, ov_end) in active_pairs.items():
        log_entry = (
            db.query(models.ConflictLog)
            .filter_by(task_1_id=lo_id, task_2_id=hi_id)
            .first()
        )
        if log_entry:
            log_entry.task_1_title = lo.title
            log_entry.task_2_title = hi.title
            log_entry.overlap_start = ov_start
            log_entry.overlap_end = ov_end
            log_entry.status = "active"
            log_entry.resolved_at = None
        else:
            db.add(
                models.ConflictLog(
                    task_1_id=lo_id,
                    task_2_id=hi_id,
                    task_1_title=lo.title,
                    task_2_title=hi.title,
                    overlap_start=ov_start,
                    overlap_end=ov_end,
                    status="active",
                )
            )
    db.commit()

    # anything that WAS active but isn't in this check's active set anymore -> resolved
    still_marked_active = (
        db.query(models.ConflictLog).filter(models.ConflictLog.status == "active").all()
    )
    for log_entry in still_marked_active:
        if (log_entry.task_1_id, log_entry.task_2_id) not in active_pairs:
            log_entry.status = "resolved"
            log_entry.resolved_at = datetime.utcnow()
    db.commit()

    active_out = [
        {
            "task_1": lo.title,
            "task_1_start": lo.start_date.isoformat(),
            "task_1_due": lo.due_date.isoformat(),
            "task_2": hi.title,
            "task_2_start": hi.start_date.isoformat(),
            "task_2_due": hi.due_date.isoformat(),
            "overlap_start": ov_start.isoformat(),
            "overlap_end": ov_end.isoformat(),
        }
        for (lo, hi, ov_start, ov_end) in active_pairs.values()
    ]

    resolved_logs = (
        db.query(models.ConflictLog)
        .filter(models.ConflictLog.status == "resolved")
        .order_by(models.ConflictLog.resolved_at.desc())
        .all()
    )
    resolved_out = [
        {
            "task_1": log.task_1_title,
            "task_2": log.task_2_title,
            "overlap_start": log.overlap_start.isoformat(),
            "overlap_end": log.overlap_end.isoformat(),
            "resolved_at": log.resolved_at.isoformat() if log.resolved_at else None,
        }
        for log in resolved_logs
    ]

    return {"active": active_out, "resolved": resolved_out}