from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct
from datetime import datetime
from collections import Counter

from app.db import models
from app.schemas import manager_chat as chat_schema
from app.db.session import get_db
from app.services.manager_ai_service import get_manager_intent_from_llm, get_manager_summary_from_llm

router = APIRouter()

def find_task_safely(db: Session, filters: dict):
    """
    Finds a task safely. Prioritizes ID, then checks for ambiguous titles.
    Returns (unique_task, ambiguous_tasks_list)
    """
    task_id = filters.get("task_id")
    task_title = filters.get("task_title")

    query_options = [
        joinedload(models.Task.dependencies),
        joinedload(models.Task.required_skills),
        joinedload(models.Task.approvals).joinedload(models.Approval.approver),
        joinedload(models.Task.comments).joinedload(models.Comment.author)
    ]

    if task_id:
        task = db.query(models.Task).options(*query_options).filter(models.Task.task_id == task_id).first()
        return (task, None) if task else (None, None)

    if task_title:
        tasks = db.query(models.Task).options(*query_options).filter(models.Task.title.ilike(task_title)).all()
        
        if len(tasks) == 1:
            return (tasks[0], None)
        elif len(tasks) > 1:
            return (None, tasks)
    
    return (None, None)
def get_manager_team_ids(db: Session, manager_id: int):
    """
    Defines a manager's team by finding all contributors whose tasks
    that manager is set to approve.
    """
    tasks_approved_by_manager = db.query(distinct(models.Task.assignee_id)).join(models.Approval).filter(
        models.Approval.approver_id == manager_id
    )
    
    team_member_ids = [t[0] for t in tasks_approved_by_manager.all() if t[0] is not None]
    return team_member_ids


@router.post("/manager-chat", response_model=chat_schema.ManagerChatResponse)
def handle_manager_chat(query: chat_schema.ManagerChatQuery, db: Session = Depends(get_db)):
    intent_data = get_manager_intent_from_llm(query.question)
    intent = intent_data.get("intent", "error")
    filters = intent_data.get("filters", {})
    output_type = intent_data.get("output_type", "text")

    # Normalize the output_type to handle AI variations
    if output_type in ['visual', 'chart']:
        output_type = 'visualization'
    
    data_for_response = {}
    raw_data_for_ai = {}
    response_data = {}
    
    team_ids = get_manager_team_ids(db, query.manager_id)

    if output_type == 'text':
        # --- COUNT QUERIES ---
        if "count_" in intent:
            if intent == "count_my_tasks":
                q = db.query(models.Task).filter(models.Task.assignee_id == query.manager_id)
                if filters.get('priority'): q = q.filter(models.Task.priority.ilike(filters['priority']))
                if filters.get('status'): q = q.filter(models.Task.status.ilike(filters['status']))
                count = q.count()
                raw_data_for_ai = {"context": "manager_task_count", "filters": filters, "count": count}
            elif intent == "count_contributors":
                count = db.query(models.User).filter(models.User.role == 'Contributor').count()
                raw_data_for_ai = {"context": "contributor_count", "count": count}
            elif intent == "count_by_availability":
                status = filters.get("availability_status")
                q = db.query(models.User).filter(
                    models.User.role == 'Contributor',
                    models.User.user_id.in_(team_ids) 
                )
                if status: q = q.filter(models.User.availability_status.ilike(status))
                count = q.count()
                raw_data_for_ai = {"context": "availability_count", "filters": filters, "count": count}
            # Find this block and add the models.User.user_id.in_(team_ids) filter
            elif intent == "count_by_skill":
                skill_name = filters.get("skill_name")
                count = db.query(models.User).join(models.user_skills_table).join(models.Skill).filter(
                    models.User.user_id.in_(team_ids),  # <-- Add this filter
                    models.Skill.name.ilike(f'%{skill_name}%')
                ).count()
                raw_data_for_ai = {"context": "skill_count", "filters": filters, "count": count}
            elif intent == "count_by_approval_status":
                status = filters.get("approval_status", "Pending")
                count = db.query(models.Approval).filter(models.Approval.status.ilike(status)).count()
                raw_data_for_ai = {"context": "approval_count", "filters": filters, "count": count}

        # --- LIST QUERIES ---
        elif intent in ["get_my_tasks", "get_contributors", "get_by_availability", "get_by_skill", "get_tasks_by_approval"]:
            if intent == "get_my_tasks":
                q = db.query(models.Task).filter(models.Task.assignee_id == query.manager_id)
                if filters.get('priority'): q = q.filter(models.Task.priority.ilike(filters['priority']))
                tasks = q.all()
                raw_data_for_ai = {"context": "manager_personal_tasks", "tasks": [t.title for t in tasks]}
            elif intent == "get_contributors":
                users = db.query(models.User).filter(models.User.role == 'Contributor').all()
                raw_data_for_ai = {"context": "list_contributors", "contributors": [u.name for u in users]}
            elif intent == "get_by_availability":
                status = filters.get("availability_status")
                users = db.query(models.User).filter(models.User.role == 'Contributor', models.User.availability_status.ilike(status)).all()
                raw_data_for_ai = {"filters": filters, "contributors": [u.name for u in users]}
            elif intent == "get_by_skill":
                skill_name = filters.get("skill_name")
                users = db.query(models.User).join(models.user_skills_table).join(models.Skill).filter(models.Skill.name.ilike(f'%{skill_name}%')).all()
                raw_data_for_ai = {"filters": filters, "contributors": [u.name for u in users]}
            elif intent == "get_tasks_by_approval":
                status = filters.get("approval_status")
                tasks = db.query(models.Task).join(models.Approval).filter(models.Approval.status.ilike(status)).all()
                raw_data_for_ai = {"filters": filters, "tasks": [f"'{t.title}' (ID: {t.task_id})" for t in tasks]}
        # Find this block and add the .filter(models.User.user_id.in_(team_ids)) line
        elif intent == "get_contributor_workload":
            name = filters.get("contributor_name")
            user = db.query(models.User).options(joinedload(models.User.tasks)).filter(
                models.User.name.ilike(f'%{name}%'),
                models.User.user_id.in_(team_ids)  # <-- Add this filter
            ).first()
            if user:
                raw_data_for_ai = {"contributor_name": user.name, "tasks": [t.title for t in user.tasks]}
        # --- ACTION & SPECIFIC GET QUERIES (with ID Safety) ---
        else:
            unique_task, ambiguous_tasks = find_task_safely(db, filters)
            
            if ambiguous_tasks:
                raw_data_for_ai = {"ambiguous_tasks": [{"id": t.task_id, "title": t.title} for t in ambiguous_tasks]}
            elif not unique_task and intent not in ['create_task']:
                 raw_data_for_ai = {"filters": filters}
            else:
                if intent == "update_task":
                    update_fields = {k: v for k, v in filters.items() if k not in ['task_title', 'task_id']}
                    for key, value in update_fields.items(): setattr(unique_task, key, value)
                    db.commit()
                    response_data = {"introduction": f"Success! Updated task '{unique_task.title}'.", "items": []}
                elif intent == "assign_task":
                    user = db.query(models.User).filter(models.User.name.ilike(f'%{filters.get("contributor_name")}%')).first()
                    if not user:
                        response_data = {"introduction": "Error: Could not find that user.", "items": []}
                    else:
                        unique_task.assignee_id = user.user_id
                        db.commit()
                        response_data = {"introduction": f"Success! Assigned '{unique_task.title}' to {user.name}.", "items": []}
                elif intent == "approve_task":
                    approval = db.query(models.Approval).filter(models.Approval.task_id == unique_task.task_id, models.Approval.status == 'Pending').first()
                    if not approval:
                        response_data = {"introduction": "Error: This task has no pending approvals.", "items": []}
                        
                    else:
                        approval.status = 'Approved'
                        approval.timestamp = datetime.now()
                        db.commit()
                        response_data = {"introduction": f"Success! Approved task '{unique_task.title}'.", "items": []}
                elif intent == "recommend_assignee":
                    required_skills = {s.name for s in unique_task.required_skills}
                    available_users = db.query(models.User).options(joinedload(models.User.skills)).filter(models.User.availability_status == 'Available', models.User.role == 'Contributor').all()
                    recommendations = [{"name": u.name, "score": int((len(required_skills.intersection({s.name for s in u.skills})) / len(required_skills)) * 100) if required_skills else 100} for u in available_users]
                    recommendations = [r for r in recommendations if r['score'] > 0]
                    recommendations.sort(key=lambda x: x["score"], reverse=True)
                    raw_data_for_ai = {"task_title": unique_task.title, "recommendations": recommendations[:3]}
                elif intent == "get_prerequisites":
                    raw_data_for_ai = {"task_title": unique_task.title, "Prerequisite Tasks": [d.title for d in unique_task.dependencies], "Required Skills": [s.name for s in unique_task.required_skills], "Description": unique_task.description}
                elif intent == "get_skill_requirements":
                     raw_data_for_ai = {"task_title": unique_task.title, "required_skills": [s.name for s in unique_task.required_skills]}
                elif intent == "get_comments":
                    raw_data_for_ai = {"task_title": unique_task.title, "comments": [f"'{c.text}' by {c.author.name}" for c in unique_task.comments]}
                elif intent == "get_approval_status":
                    raw_data_for_ai = {"task_title": unique_task.title, "approvals": [f"{a.status} by {a.approver.name}" for a in unique_task.approvals]}
                elif intent == "get_task_timeline":
                    raw_data_for_ai = {"task_title": unique_task.title, "Timeline": f"Estimated: {unique_task.estimated_start_date.strftime('%b %d')} to {unique_task.estimated_end_date.strftime('%b %d')}"}
                elif intent == "create_task":
                    project = db.query(models.Project).filter(models.Project.name.ilike(f'%{filters.get("project_name")}%')).first()
                    if not project:
                        response_data = {"introduction": f"Error: Project '{filters.get('project_name')}' not found.", "items": []}
                    else:
                        new_task = models.Task(title=filters.get("title"), project_id=project.project_id)
                        db.add(new_task)
                        db.commit()
                        response_data = {"introduction": f"Success! Created task '{new_task.title}'.", "items": []}
        
        if not raw_data_for_ai and not response_data:
            response_data = {"introduction": "I'm sorry, I didn't understand that request.", "items": []}
        elif raw_data_for_ai:
            response_data = get_manager_summary_from_llm(raw_data_for_ai)
        
        data_for_response = chat_schema.TextData(**response_data)

    # Find this block and add the .filter(models.User.user_id.in_(team_ids)) line
    elif output_type == "visualization":
        if intent == "visualize_team_workload":
            team_members = db.query(models.User).options(joinedload(models.User.tasks)).filter(
                models.User.user_id.in_(team_ids)  # <-- Add this filter
            ).all()
            labels = [c.name for c in team_members]
            values = [len(c.tasks) for c in team_members]
            data_for_response = chat_schema.ChartData(chart_type='bar', title="Current Task Load for My Team", labels=labels, values=values)
        # Find this block and add the .filter(models.user_skills_table.c.user_id.in_(team_ids)) line
        elif intent == "visualize_skill_distribution":
            skill_counts = db.query(models.Skill.name, func.count(models.user_skills_table.c.user_id)).join(
                models.user_skills_table
            ).filter(
                models.user_skills_table.c.user_id.in_(team_ids)  # <-- Add this filter
            ).group_by(models.Skill.name).all()
            labels = [name for name, count in skill_counts]
            values = [count for name, count in skill_counts]
            data_for_response = chat_schema.ChartData(chart_type='pie', title="Skill Distribution Across My Team", labels=labels, values=values)
        elif intent == "visualize_project_health":
            projects = db.query(models.Project).options(joinedload(models.Project.tasks)).all()
            labels = [p.name for p in projects]
            values = [int((sum(1 for t in p.tasks if t.status == 'Done') / len(p.tasks)) * 100) if p.tasks else 0 for p in projects]
            data_for_response = chat_schema.ChartData(chart_type='bar', title="Project Completion Health (%)", labels=labels, values=values)
        else:
             data_for_response = chat_schema.ChartData(chart_type='bar', title="No Data", labels=[], values=[])
    
    else: # Graceful fallback for any other unexpected output_type
        output_type = 'text'
        response_data = {"introduction": "I encountered an internal error processing that request.", "items": []}
        data_for_response = chat_schema.TextData(**response_data)


    final_answer = chat_schema.ManagerChatAnswer(output_type=output_type, data=data_for_response)
    return chat_schema.ManagerChatResponse(answer=final_answer)