from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from collections import Counter

from app.db import models
from app.schemas import manager_chat as chat_schema
from app.db.session import get_db
from app.services.manager_ai_service import get_manager_intent_from_llm, get_manager_summary_from_llm

router = APIRouter()

@router.post("/manager-chat", response_model=chat_schema.ManagerChatResponse)
def handle_manager_chat(query: chat_schema.ManagerChatQuery, db: Session = Depends(get_db)):
    intent_data = get_manager_intent_from_llm(query.question)
    intent = intent_data.get("intent", "error")
    filters = intent_data.get("filters", {})
    output_type = intent_data.get("output_type", "text")
    
    data_for_response = {}

    if output_type == "text":
        response_data = {}
        if intent == "get_contributor_workload":
            name = filters.get("contributor_name")
            user = db.query(models.User).options(joinedload(models.User.tasks)).filter(models.User.name.ilike(f'%{name}%')).first()
            if user:
                raw_data = {"contributor_name": user.name, "tasks": [{"id": t.task_id, "title": t.title} for t in user.tasks]}
                response_data = get_manager_summary_from_llm(raw_data)
        
        elif intent == "find_available_contributors":
            users = db.query(models.User).filter(models.User.availability_status == 'Available', models.User.role == 'Contributor').all()
            raw_data = {"available_contributors": [u.name for u in users]}
            response_data = get_manager_summary_from_llm(raw_data)

        elif intent == "find_contributors_by_skill":
            skill_name = filters.get("skill_name")
            users = db.query(models.User).join(models.User.skills).filter(models.Skill.name.ilike(f'%{skill_name}%')).all()
            raw_data = {"skill": skill_name, "contributors": [u.name for u in users]}
            response_data = get_manager_summary_from_llm(raw_data)

        elif intent == "create_task":
            project = db.query(models.Project).filter(models.Project.name.ilike(f'%{filters.get("project_name")}%')).first()
            if project:
                new_task = models.Task(
                    title=filters.get("title"),
                    project_id=project.project_id,
                    priority=filters.get("priority", "Medium"),
                )
                skill_names = filters.get("required_skills", [])
                if skill_names:
                    skills_to_add = db.query(models.Skill).filter(models.Skill.name.in_(skill_names)).all()
                    new_task.required_skills = skills_to_add
                
                db.add(new_task)
                db.commit()
                response_data = {"introduction": f"Success! I've created the task '{new_task.title}' in the '{project.name}' project.", "items": []}
            else:
                response_data = {"introduction": "I'm sorry, I couldn't find a project with that name.", "items": []}
    
        elif intent == "recommend_assignee":
            task_title = filters.get("task_title")
            task = db.query(models.Task).options(joinedload(models.Task.required_skills)).filter(models.Task.title.ilike(f'%{task_title}%')).first()
            
            if task:
                required_skills = {s.name for s in task.required_skills}
                available_users = db.query(models.User).options(joinedload(models.User.skills)).filter(models.User.availability_status == 'Available', models.User.role == 'Contributor').all()
                
                recommendations = []
                for user in available_users:
                    user_skills = {s.name for s in user.skills}
                    match_count = len(required_skills.intersection(user_skills))
                    score = int((match_count / len(required_skills)) * 100) if required_skills else 100
                    if score > 0:
                        recommendations.append({"name": user.name, "score": score})
                
                recommendations.sort(key=lambda x: x["score"], reverse=True)
                raw_data = {"task_title": task.title, "recommendations": recommendations[:3]}
                response_data = get_manager_summary_from_llm(raw_data)
            else:
                response_data = {"introduction": "I couldn't find a task with that title.", "items": []}
                
        if not response_data:
            response_data = {"introduction": "I'm sorry, I didn't understand that request. Please try rephrasing.", "items": []}

        data_for_response = chat_schema.TextData(**response_data)

    elif output_type == "visualization":
        if intent == "visualize_team_workload":
            contributors = db.query(models.User).options(joinedload(models.User.tasks)).filter(models.User.role == 'Contributor').all()
            labels = [c.name for c in contributors]
            values = [len(c.tasks) for c in contributors]
            data_for_response = chat_schema.ChartData(chart_type='bar', title="Current Task Load per Contributor", labels=labels, values=values)
        
        elif intent == "visualize_skill_distribution":
            # --- THIS IS THE FIX ---
            # Use the correct table name: user_skills_table
            skill_counts = db.query(
                models.Skill.name, 
                func.count(models.user_skills_table.c.user_id)
            ).join(
                models.user_skills_table
            ).group_by(models.Skill.name).all()
            
            labels = [name for name, count in skill_counts]
            values = [count for name, count in skill_counts]
            data_for_response = chat_schema.ChartData(chart_type='pie', title="Skill Distribution Across Team", labels=labels, values=values)

        elif intent == "visualize_project_health":
            projects = db.query(models.Project).options(joinedload(models.Project.tasks)).all()
            labels = [p.name for p in projects]
            values = [int((sum(1 for t in p.tasks if t.status == 'Done') / len(p.tasks)) * 100) if p.tasks else 0 for p in projects]
            data_for_response = chat_schema.ChartData(chart_type='bar', title="Project Completion Health (%)", labels=labels, values=values)
        
        else:
             data_for_response = chat_schema.ChartData(chart_type='bar', title="No Data", labels=[], values=[])

    final_answer = chat_schema.ManagerChatAnswer(output_type=output_type, data=data_for_response)
    return chat_schema.ManagerChatResponse(answer=final_answer)