from pydantic import BaseModel
from typing import List, Optional
from .task import Task # Import the Task schema

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    project_id: int
    tasks: List[Task] = [] # Include tasks when fetching a project

    class Config:
        from_attributes = True