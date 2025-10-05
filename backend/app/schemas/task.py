#
# FILE: backend/app/schemas/task.py
#

from pydantic import BaseModel
import datetime
from typing import Optional, List

# --- FIX: We can no longer import User directly at the top ---

# Schema for creating a new task (input)
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = 'Medium'
    project_id: int
    assignee_id: Optional[int] = None

# Schema for reading a task (output)
class Task(BaseModel):
    task_id: int
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    project_id: int
    
    # --- FIX: Use a forward reference for the assignee as well ---
    assignee: Optional["User"] = None

    class Config:
        from_attributes = True


# --- IMPORTANT: Rebuild models to resolve the forward references ---
# After all models that reference each other have been defined, we can now
# safely import them and tell Pydantic to resolve the string references.
from .user import User, UserDashboard

UserDashboard.model_rebuild()
Task.model_rebuild()