from pydantic import BaseModel, EmailStr
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .task import Task

# --- THIS IS THE NEW PART ---
# Schema for validating the login request body
class UserLogin(BaseModel):
    email: EmailStr # Use EmailStr for automatic email validation

# Schema for basic user info in API responses
class User(BaseModel):
    user_id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

# Schema for the user's task statistics
class UserStats(BaseModel):
    total_tasks: int
    tasks_todo: int
    tasks_inprogress: int
    tasks_done: int

# A combined model for the entire dashboard
class UserDashboard(BaseModel):
    user_info: User
    stats: UserStats
    tasks: List["Task"]