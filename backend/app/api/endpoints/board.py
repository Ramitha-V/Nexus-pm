#
# FILE: backend/app/api/endpoints/board.py
#
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.schemas import board as board_schema
from app.db.session import get_db

router = APIRouter()

# Define the columns for our Kanban board
BOARD_COLUMNS = ["To Do", "In Progress", "Done"]

@router.get("/project/{project_id}/board", response_model=board_schema.KanbanBoard)
def get_project_board_data(project_id: int, db: Session = Depends(get_db)):
    """
    Fetches all tasks for a specific project, grouped by status,
    to populate the Kanban board.
    """
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    tasks = db.query(models.Task).options(
        joinedload(models.Task.assignee) # Eager load the assignee details
    ).filter(
        models.Task.project_id == project_id
    ).all()

    # Group tasks by their status
    tasks_by_status = {col: [] for col in BOARD_COLUMNS}
    for task in tasks:
        if task.status in tasks_by_status:
            assignee_name = task.assignee.name if task.assignee else "Unassigned"
            tasks_by_status[task.status].append(
                board_schema.KanbanCard(
                    task_id=task.task_id,
                    title=task.title,
                    priority=task.priority,
                    assignee_name=assignee_name
                )
            )

    # Build the final board structure
    columns = [
        board_schema.KanbanColumn(title=status, cards=cards)
        for status, cards in tasks_by_status.items()
    ]
    
    return board_schema.KanbanBoard(
        project_id=project.project_id,
        project_name=project.name,
        columns=columns
    )

@router.put("/tasks/{task_id}/status", status_code=status.HTTP_204_NO_CONTENT)
def update_task_status(task_id: int, status_update: board_schema.TaskStatusUpdate, db: Session = Depends(get_db)):
    """
    Updates the status of a task when it's dragged and dropped.
    """
    task = db.query(models.Task).filter(models.Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if the new status is valid
    if status_update.status not in BOARD_COLUMNS:
        raise HTTPException(status_code=400, detail="Invalid status column")
    
    task.status = status_update.status
    db.commit()
    return