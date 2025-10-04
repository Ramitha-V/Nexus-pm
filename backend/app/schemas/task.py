from pydantic import BaseModel
import datetime
from typing import Optional

# Import the models from the user schema file
from .user import User, UserDashboard

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
    status: str
    priority: str
    project_id: int
    assignee: Optional[User] = None 

    class Config:
        from_attributes = True

# --- THIS IS THE FIX ---
# Now that the 'Task' model is fully defined, we tell the UserDashboard
# model to resolve its forward reference to 'Task'.
UserDashboard.model_rebuild()

