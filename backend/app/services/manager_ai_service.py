import google.generativeai as genai
import json
from typing import Any, Dict
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
MODEL_NAME = 'gemini-2.5-flash'

intent_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
intent_prompt = """
Your job is to be an expert query classifier for a project manager. You must generate a JSON object describing their intent.
The JSON must have "output_type", "intent", and "filters".

POSSIBLE INTENTS & THEIR FILTERS:
- "get_my_tasks", "count_my_tasks": Manager's own tasks. Filters: 'priority', 'status'.
- "get_contributors", "count_contributors": List or count all contributors.
- "get_by_availability", "count_by_availability": List or count contributors by availability. Filters: 'availability_status'.
- "get_by_skill", "count_by_skill": List or count contributors by skill. Filters: 'skill_name'.
- "get_tasks_by_approval", "count_by_approval_status": List or count tasks by approval status. Filters: 'approval_status'.
- "get_prerequisites": Find prerequisites for a task. Filters: 'task_title'.
- "get_skill_requirements": Find ONLY skills for a task. Filters: 'task_title'.
- "get_comments": Find ONLY comments for a task. Filters: 'task_title'.
- "get_approval_status": Find ONLY approval status for a task. Filters: 'task_title'.
- "get_task_timeline": Find ONLY dates for a task. Filters: 'task_title'.
- "create_task": Create a task. Filters: 'title', 'project_name', 'description', etc.
- "update_task": Update a task. Filters: 'task_title' and/or 'task_id', plus fields to update.
- "recommend_assignee": Recommend an assignee. Filters: 'task_title' and/or 'task_id'.
- "assign_task": Assign a task. Filters: 'task_title' and/or 'task_id', 'contributor_name'.
- "approve_task": Approve a task. Filters: 'task_title' and/or 'task_id'.
- "visualize_team_workload", "visualize_skill_distribution", "visualize_project_health": Visualization intents.
- "get_contributor_workload": A specific contributor's tasks. Filters: 'contributor_name'.

RULES:
- "list", "who are", "show me" implies a "get_" intent. "how many", "count" implies a "count_" intent.
- Action verbs like "update", "assign", "approve", "create" MUST use their specific intents.
- If the user provides a task ID (e.g., "update task ID 123"), you MUST extract it as 'task_id'.
- "what is [person's name] working on?" MUST use "get_contributor_workload".
- Respond ONLY with the JSON object.

Example 1 (List Skills):
User: "who knows Python?"
Response: {"output_type": "text", "intent": "get_by_skill", "filters": {"skill_name": "Python"}}

Example 2 (Count Skills):
User: "how many people know Python?"
Response: {"output_type": "text", "intent": "count_by_skill", "filters": {"skill_name": "Python"}}

Example 3 (Update with ID):
User: "update task ID 145 and set the priority to high"
Response: {"output_type": "text", "intent": "update_task", "filters": {"task_id": 145, "priority": "High"}}
"""

summary_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
summary_prompt = """
ROLE: You are Nexus, a helpful assistant to a project manager.
TASK: Based on the provided JSON data, generate a structured JSON response with "introduction" and "items" keys.
- "introduction": A friendly, one-sentence summary that SPECIFICALLY mentions the context.
- "items": An array of strings for any lists.

RULES:
- If the input has a "no_results_for" key, state that no items were found for that query.
- If the input has an "ambiguous_tasks" key, you MUST list the tasks with their IDs and instruct the user to be more specific.

EXAMPLE (Ambiguous Task):
Input: {"ambiguous_tasks": [{"id": 101, "title": "Design the API"}, {"id": 105, "title": "Design the API"}]}
Response:
{
  "introduction": "I found multiple tasks with that name. Please be more specific by using the task ID in your next command:",
  "items": ["ID 101: Design the API", "ID 105: Design the API"]
}
Now, generate the JSON response for the following data:
"""

def get_manager_intent_from_llm(question: str) -> Dict[str, Any]:
    try:
        full_prompt = f"{intent_prompt}\nUser question: \"{question}\"\nResponse:"
        response = intent_model.generate_content(full_prompt)
        intent_data = json.loads(response.text)
        print(f"Manager AI Service: Received intent from Gemini: {intent_data}")
        return intent_data
    except Exception as e:
        print(f"Manager AI Service ERROR (Intent Extraction): {e}")
        return {"output_type": "text", "intent": "error", "filters": {}}

def get_manager_summary_from_llm(data: Any) -> Dict:
    is_empty = not data or (isinstance(data, dict) and "count" not in data and not any(v for k, v in data.items() if k != 'filters'))
    if is_empty:
        context = {"no_results_for": data if isinstance(data, dict) else {}}
        data_json = json.dumps(context)
    else:
        if isinstance(data, dict): data_for_ai = {k: v for k, v in data.items() if v or k in ['filters', 'count']}
        else: data_for_ai = data
        data_json = json.dumps(data_for_ai, indent=2)
    try:
        full_prompt = f"{summary_prompt}\n{data_json}"
        response = summary_model.generate_content(full_prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"Manager AI Service ERROR (Summary Generation): {e}")
        return {"introduction": "I had some trouble generating a summary.", "items": []}