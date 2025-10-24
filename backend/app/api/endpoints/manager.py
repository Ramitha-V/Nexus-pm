from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from collections import Counter

from app.db import models
from app.db.session import get_db

router = APIRouter()

@router.get("/manager/overview-stats")
def get_manager_overview_stats(db: Session = Depends(get_db)):
    total_projects = db.query(models.Project).count()
    total_contributors = db.query(models.User).filter(models.User.role == 'Contributor').count()
    
    # --- FINAL CHANGE: Calculate Pending Approvals instead of Overdue Tasks ---
    pending_approvals = db.query(models.Approval).filter(models.Approval.status == 'Pending').count()
    
    return {
        "total_projects": total_projects,
        "total_contributors": total_contributors,
        "pending_approvals": pending_approvals, # Return the new metric
    }

@router.get("/manager/dashboard-charts")
def get_dashboard_charts(db: Session = Depends(get_db)):
    # 1. Project Health Data
    projects = db.query(models.Project).options(joinedload(models.Project.tasks)).all()
    project_health = []
    for p in projects:
        total = len(p.tasks)
        done = sum(1 for t in p.tasks if t.status == 'Done')
        completion = int((done / total) * 100) if total > 0 else 0
        project_health.append({"name": p.name, "completion": completion})

    # 2. Overall Task Status & Priority Data
    all_tasks = db.query(models.Task).all()
    status_counts = Counter(t.status for t in all_tasks)
    priority_counts = Counter(t.priority for t in all_tasks)

    # 3. Resource Utilization Data
    resources = db.query(models.Resource).all()
    resource_utilization = []
    for r in resources:
        usage_count = db.query(models.Task).filter(models.Task.required_resources.any(models.Resource.resource_id == r.resource_id), models.Task.status == 'In Progress').count()
        resource_utilization.append({"name": r.name, "usage": usage_count})

    return {
        "project_health": project_health,
        "overall_status": {
            "labels": list(status_counts.keys()),
            "values": list(status_counts.values())
        },
        "overall_priority": {
            "labels": list(priority_counts.keys()),
            "values": list(priority_counts.values())
        },
        "resource_utilization": resource_utilization
    }

@router.get("/manager/projects-summary")
def get_projects_summary(db: Session = Depends(get_db)):
    projects = db.query(models.Project).options(joinedload(models.Project.tasks)).order_by(models.Project.name).all()
    summary = [{"project_id": p.project_id, "name": p.name, "task_count": len(p.tasks), "completion_percent": int((sum(1 for t in p.tasks if t.status == 'Done') / len(p.tasks)) * 100) if len(p.tasks) > 0 else 0, "end_date": p.end_date.strftime('%B %d, %Y') if p.end_date else "N/A"} for p in projects]
    return summary

@router.get("/manager/contributors-summary")
def get_contributors_summary(db: Session = Depends(get_db)):
    contributors = db.query(models.User).options(joinedload(models.User.skills), joinedload(models.User.tasks)).filter(models.User.role == 'Contributor').order_by(models.User.name).all()
    summary = [{"user_id": c.user_id, "name": c.name, "availability": c.availability_status, "skills": [s.name for s in c.skills], "task_load": len(c.tasks)} for c in contributors]
    return summary

@router.get("/manager/project-timeline/{project_id}")
def get_project_timeline_data(project_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all tasks for a specific project, formatted for a Gantt chart.
    """
    tasks = db.query(models.Task).filter(
        models.Task.project_id == project_id,
        models.Task.estimated_start_date.isnot(None),
        models.Task.estimated_end_date.isnot(None)
    ).order_by(models.Task.estimated_start_date).all()

    if not tasks:
        return []

    gantt_data = []
    for task in tasks:
        gantt_data.append({
            "id": task.task_id,
            "title": task.title,
            "start": task.estimated_start_date,
            "end": task.estimated_end_date,
            "status": task.status
        })
        
    return gantt_data