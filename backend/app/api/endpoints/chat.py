from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db import models
from app.schemas import chat as chat_schema
from app.db.session import get_db
# Correctly import the new function names from your ai_service.py file
from app.services.ai_service import get_intent_from_llm, get_natural_language_summary_from_llm

router = APIRouter()

@router.post("/chat", response_model=chat_schema.ChatResponse)
def handle_chat_query(query: chat_schema.ChatQuery, db: Session = Depends(get_db)):
    # 1. AI extracts the user's intent and filters using the new function
    intent_data = get_intent_from_llm(query.question)
    intent = intent_data.get("intent", "get_tasks")
    filters = intent_data.get("filters", {})
    
    response_data = []

    # 2. Execute logic based on the identified intent
    if intent == "get_tasks":
        db_query = db.query(models.Task).filter(models.Task.assignee_id == query.user_id)
        if filters.get('priority'):
            db_query = db_query.filter(models.Task.priority == filters['priority'])
        if filters.get('status'):
            db_query = db_query.filter(models.Task.status == filters['status'])
        
        tasks = db_query.all()
        response_data = [{"title": t.title} for t in tasks]

    elif intent == "get_overdue":
        db_query = db.query(models.Task).filter(
            models.Task.assignee_id == query.user_id,
            models.Task.status != 'Done',
            models.Task.estimated_end_date < datetime.now()
        )
        if filters.get('priority'):
            db_query = db_query.filter(models.Task.priority == filters['priority'])
            
        tasks = db_query.all()
        response_data = [{"title": t.title, "due_date": t.estimated_end_date.strftime('%Y-%m-%d')} for t in tasks]

    elif intent == "get_dependencies":
        task_title_from_ai = filters.get("task_title")
        if task_title_from_ai:
            task = db.query(models.Task).filter(
                models.Task.assignee_id == query.user_id,
                models.Task.title.ilike(f'%{task_title_from_ai}%')
            ).first()

            if task:
                response_data = {
                    "task_title": task.title,
                    "dependencies": [dep.title for dep in task.dependencies] if task.dependencies else []
                }
    
    # 3. AI generates a friendly summary of the results using the new function
    summary_text = get_natural_language_summary_from_llm(response_data)
    
    # 4. FIX: Construct the required StructuredAnswer object
    # Since the AI returns a full text block, we place it in the introduction.
    response_object = chat_schema.StructuredAnswer(
        introduction=summary_text,
        tasks=[]
    )
    
    return chat_schema.ChatResponse(answer=response_object)

