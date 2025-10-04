from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.schemas import user as user_schema
from app.db.session import get_db

router = APIRouter()

# Login Endpoint
@router.post("/login", response_model=user_schema.User)
def login_user(user_in: user_schema.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Dashboard Data Endpoint
@router.get("/users/{user_id}/dashboard", response_model=user_schema.UserDashboard)
def get_user_dashboard(user_id: int, db: Session = Depends(get_db)):
    # Eagerly load the tasks related to the user to avoid extra queries
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # The tasks are already loaded on the user object because of the 'relationship' backref
    tasks = user.tasks 
    
    stats = user_schema.UserStats(
        total_tasks=len(tasks),
        tasks_todo=sum(1 for t in tasks if t.status == 'To Do'),
        tasks_inprogress=sum(1 for t in tasks if t.status == 'In Progress'),
        tasks_done=sum(1 for t in tasks if t.status == 'Done'),
    )

    # We can now construct the dashboard data with confidence
    dashboard_data = user_schema.UserDashboard(
        user_info=user,
        stats=stats,
        tasks=tasks
    )
    
    return dashboard_data