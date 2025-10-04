from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, timedelta
from collections import Counter

from app.db import models
from app.schemas import chat as chat_schema
from app.db.session import get_db
from app.services.ai_service import get_intent_from_llm, get_text_summary_from_llm

router = APIRouter()

def format_date(dt):
    return dt.strftime('%B %d, %Y') if dt else "Not set"

def parse_timeframe(timeframe: str) -> (date, date):
    today = date.today()
    timeframe = timeframe.lower()
    if "today" in timeframe: return today, today
    if "this week" in timeframe:
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    return None, None # Simplified for brevity

@router.post("/chat", response_model=chat_schema.ChatResponse)
def handle_chat_query(query: chat_schema.ChatQuery, db: Session = Depends(get_db)):
    intent_data = get_intent_from_llm(query.question)
    output_type = intent_data.get("output_type", "text")
    intent = intent_data.get("intent", "get_tasks")
    filters = intent_data.get("filters", {})
    
    data_for_response = {}

    if output_type == "text":
        raw_data_for_ai = {}
        
        def find_task(task_title: str):
            if not task_title: return None
            return db.query(models.Task).options(
                joinedload(models.Task.dependencies), joinedload(models.Task.required_skills),
                joinedload(models.Task.approvals).joinedload(models.Approval.approver),
                joinedload(models.Task.comments).joinedload(models.Comment.author)
            ).filter(models.Task.title.ilike(f'%{task_title}%'), models.Task.assignee_id == query.user_id).first()

        task_title = filters.get("task_title")
        task = find_task(task_title)

        project_name = filters.get("project_name")
        project = None
        if project_name:
            project = db.query(models.Project).filter(models.Project.name.ilike(f'%{project_name}%')).first()

        if intent == "get_tasks":
            q = db.query(models.Task).filter(models.Task.assignee_id == query.user_id)
            if filters.get('priority'): q = q.filter(models.Task.priority.ilike(filters['priority']))
            if filters.get('status'): q = q.filter(models.Task.status.ilike(filters['status']))
            tasks = q.all()
            raw_data_for_ai = {"filters": filters, "tasks": [t.title for t in tasks]}
        
        elif intent == "get_overdue":
            q = db.query(models.Task).filter(models.Task.assignee_id == query.user_id, models.Task.status != 'Done', models.Task.estimated_end_date < datetime.now())
            tasks = q.all()
            raw_data_for_ai = {"filters": filters, "overdue_tasks": [t.title for t in tasks]}

        elif intent == "get_approved_tasks":
            status_filter = filters.get('approval_status', 'Approved')
            tasks = db.query(models.Task).join(models.Approval).filter(
                models.Task.assignee_id == query.user_id,
                models.Approval.status.ilike(f'%{status_filter}%')
            ).all()
            raw_data_for_ai = {"filters": filters, "approved_tasks": [t.title for t in tasks]}

        elif intent == "get_prerequisites" and task:
            raw_data_for_ai = {
                "task_title": task.title,
                "Prerequisite Tasks": [d.title for d in task.dependencies],
                "Required Skills": [s.name for s in task.required_skills],
                "Description": task.description,
                "Comments": [f"'{c.text}' by {c.author.name}" for c in task.comments]
            }
        
        elif intent == "get_skill_requirements" and task:
            raw_data_for_ai = {"task_title": task.title, "required_skills": [s.name for s in task.required_skills]}

        elif intent == "get_comments" and task:
            raw_data_for_ai = {"task_title": task.title, "comments": [f"'{c.text}' by {c.author.name}" for c in task.comments]}

        elif intent == "get_approval_status" and task:
             raw_data_for_ai = {"task_title": task.title, "approvals": [f"{a.status} by {a.approver.name}" for a in task.approvals]}

        elif intent == "get_task_timeline" and task:
            raw_data_for_ai = {
                "task_title": task.title,
                "Estimated Start": format_date(task.estimated_start_date),
                "Estimated End": format_date(task.estimated_end_date),
                "Actual Start": format_date(task.actual_start_date),
                "Actual End": format_date(task.actual_end_date),
            }
        
        elif intent == "get_project_timeline" and project:
            raw_data_for_ai = {
                "project_title": project.name,
                "Project Start": format_date(project.start_date),
                "Project End": format_date(project.end_date)
            }

        elif intent == "get_task_details" and task:
            raw_data_for_ai = {
                "Title": task.title, "Status": task.status, "Priority": task.priority,
                "Description": task.description,
                "Prerequisite Tasks": [d.title for d in task.dependencies],
                "Required Skills": [s.name for s in task.required_skills],
                "Approvals": [f"{a.status} by {a.approver.name}" for a in task.approvals],
                "Timeline": f"Est. End: {format_date(task.estimated_end_date)}"
            }
        else:
             raw_data_for_ai = {"filters": filters}

        summary_json = get_text_summary_from_llm(raw_data_for_ai)
        data_for_response = chat_schema.TextData(**summary_json)

    elif output_type == "visualization":
        if intent == "get_project_summary":
            proj_name = filters.get("project_name")
            project = db.query(models.Project).options(joinedload(models.Project.tasks)).filter(models.Project.name.ilike(f'%{proj_name}%')).first()
            if not project: raise HTTPException(404, "Project not found")
            status_counts = Counter(t.status for t in project.tasks)
            data_for_response = chat_schema.ChartData(chart_type='pie', title=f"Status Summary for '{project.name}'", labels=list(status_counts.keys()), values=list(status_counts.values()))
        
        elif intent == "get_workload_distribution":
            projects = db.query(models.Project).options(joinedload(models.Project.tasks)).all()
            workload = {p.name: sum(1 for t in p.tasks if t.assignee_id == query.user_id) for p in projects}
            workload = {k: v for k, v in workload.items() if v > 0}
            data_for_response = chat_schema.ChartData(chart_type='bar', title="My Task Distribution by Project", labels=list(workload.keys()), values=list(workload.values()))
            
        elif intent == "get_priority_distribution":
            tasks = db.query(models.Task).filter(models.Task.assignee_id == query.user_id).all()
            priority_counts = Counter(t.priority for t in tasks)
            data_for_response = chat_schema.ChartData(chart_type='doughnut', title="My Tasks by Priority", labels=list(priority_counts.keys()), values=list(priority_counts.values()))
        else:
            data_for_response = chat_schema.ChartData(chart_type='bar', title="No Data", labels=[], values=[])


    final_answer = chat_schema.ChatAnswer(output_type=output_type, data=data_for_response)
    return chat_schema.ChatResponse(answer=final_answer)