import google.generativeai as genai
import json
from typing import Any, Dict
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)
generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
MODEL_NAME = 'gemini-2.5-flash'

intent_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
intent_prompt = """
Your job is to be an expert query classifier for a project manager. Analyze the user's request and generate a JSON object describing their intent.
The JSON must have "output_type", "intent", and "filters".

POSSIBLE INTENTS & THEIR FILTERS:
1.  "get_contributor_workload": Find tasks for a specific user. Filters: 'contributor_name'.
2.  "find_available_contributors": Find users whose status is 'Available'. No filters.
3.  "find_contributors_by_skill": Find users with a specific skill. Filters: 'skill_name'.
4.  "create_task": Create a new task. Filters: 'title', 'project_name', 'priority', 'required_skills'.
5.  "recommend_assignee": Recommend the best person for a task. Filters: 'task_title'.
6.  "assign_task": Assign a task to a specific person. Filters: 'task_title', 'contributor_name'.
7.  "visualize_team_workload": Chart the number of tasks per contributor. (No filters). (Output: 'visualization')
8.  "visualize_skill_distribution": Chart the skills across the team. (No filters). (Output: 'visualization')
9.  "visualize_project_health": Chart the completion status of all projects. (No filters). (Output: 'visualization')

RULES:
- A question about creating a task MUST use "create_task".
- A question about "who should" or "best person for" a task MUST use "recommend_assignee".
- A question about a specific person's work MUST use "get_contributor_workload".
- Respond ONLY with the JSON object.

Example 1 (Create Task):
User: "create a new high-priority task 'Design the API schema' for the 'SOLIDWORKS 2026' project, it needs Python skills"
Response: {"output_type": "text", "intent": "create_task", "filters": {"title": "Design the API schema", "project_name": "SOLIDWORKS 2026 Rollout", "priority": "High", "required_skills": ["Python"]}}

Example 2 (Recommend Assignee):
User: "who is the best person to assign the task 'Optimize the geometry kernel' to?"
Response: {"output_type": "text", "intent": "recommend_assignee", "filters": {"task_title": "Optimize the geometry kernel"}}

Example 3 (Visualize Workload):
User: "show me a chart of my team's workload"
Response: {"output_type": "visualization", "intent": "visualize_team_workload", "filters": {}}

Example 4 (Visualize Skills):
User: "can you visualize the skill distribution on my team?"
Response: {"output_type": "visualization", "intent": "visualize_skill_distribution", "filters": {}}
"""

summary_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
summary_prompt = """
ROLE: You are Nexus, a helpful assistant to a project manager.
TASK: Based on the provided JSON data, generate a structured JSON response with "introduction" and "items" keys.
- "introduction": A friendly, one-sentence summary that SPECIFICALLY mentions the context.
- "items": An array of strings for any lists.

EXAMPLE (Contributor Workload):
Input: {"contributor_name": "Blake Choi", "tasks": [{"id": 101, "title": "Design the API"}, {"id": 105, "title": "Design the API"}]}
Response:
{
  "introduction": "Here are all 2 tasks currently assigned to Blake Choi:",
  "items": [
    "Task #101: Design the API",
    "Task #105: Design the API"
  ]
}

EXAMPLE (Recommendation):
Input: {"task_title": "Task A", "recommendations": [{"name": "Beth Jones", "score": 100}, {"name": "David Rivera", "score": 50}]}
Response:
{
  "introduction": "Based on availability and skill match, here are my recommendations for the task 'Task A':",
  "items": ["1. Beth Jones (Skill Match: 100%)", "2. David Rivera (Skill Match: 50%)"]
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
    is_empty = not data or (isinstance(data, dict) and not any(v for k, v in data.items() if k != 'filters'))
    if is_empty:
        return {"introduction": "I couldn't find any information matching your request.", "items": []}
    try:
        data_json = json.dumps(data, indent=2)
        full_prompt = f"{summary_prompt}\n{data_json}"
        response = summary_model.generate_content(full_prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"Manager AI Service ERROR (Summary Generation): {e}")
        return {"introduction": "I had someaa trouble generating a summary.", "items": []}