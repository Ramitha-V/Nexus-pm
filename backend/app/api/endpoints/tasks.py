from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.db import models
from app.schemas import task as task_schema
from app.db.session import get_db

router = APIRouter()

@router.get("/tasks/", response_model=List[task_schema.Task])
def read_tasks(db: Session = Depends(get_db)):
    """
    Retrieve all tasks.
    """
    # Use joinedload to efficiently fetch the related assignee (User) data
    tasks = db.query(models.Task).options(joinedload(models.Task.assignee)).all()
    return tasks

# The create_task function remains the same, no changes needed there yet.
@router.post("/tasks/", response_model=task_schema.Task)
def create_task(task: task_schema.TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new task.
    """
    new_task = models.Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        project_id=task.project_id,
        assignee_id=task.assignee_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task