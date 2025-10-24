#
# FILE: backend/app/schemas/board.py
#
from pydantic import BaseModel
from typing import List, Optional

# Defines the data for a single draggable task card
class KanbanCard(BaseModel):
    task_id: int
    title: str
    priority: str
    assignee_name: Optional[str] = "Unassigned"

    class Config:
        from_attributes = True

# Defines the data for a single column (e.g., "To Do")
class KanbanColumn(BaseModel):
    title: str
    cards: List[KanbanCard]

# The complete board model
class KanbanBoard(BaseModel):
    project_id: int
    project_name: str
    columns: List[KanbanColumn]

# The request body for updating a task's status
class TaskStatusUpdate(BaseModel):
    status: str