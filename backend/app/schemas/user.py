#
# FILE: backend/app/schemas/user.py
#

from pydantic import BaseModel, EmailStr
from typing import List, Optional

# This model is for the login request body
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# This is the main User model for API responses
class User(BaseModel):
    user_id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_tasks: int
    tasks_todo: int
    tasks_inprogress: int
    tasks_done: int

class UserDashboard(BaseModel):
    user_info: User
    stats: UserStats
    # --- FIX: Use a forward reference (string) to break the import cycle ---
    tasks: List["Task"]

    class Config:
        from_attributes = True