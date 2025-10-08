import google.generativeai as genai
import json
from typing import List, Dict, Any
from app.core.config import settings


genai.configure(api_key=settings.GEMINI_API_KEY)
generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
MODEL_NAME = 'gemini-2.5-flash'

intent_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
intent_prompt = """
Your job is to be an expert query classifier. Analyze the user's question and generate a JSON object describing their intent.
The JSON must have "output_type" ('text' or 'visualization'), "intent", and "filters".

POSSIBLE INTENTS & THEIR FILTERS:
1.  "get_tasks": Find user's tasks. Filters: 'priority', 'status'.
2.  "get_overdue": Find user's late tasks. Filters: 'priority'.
3.  "get_approved_tasks": Find tasks with a specific approval status. Filters: 'approval_status'.
4.  "get_prerequisites": Find the direct prerequisites for a task. Filters: 'task_title'.
5.  "get_skill_requirements": Find ONLY the required skills for a task. Filters: 'task_title'.
6.  "get_comments": Find ONLY the comments for a task. Filters: 'task_title'.
7.  "get_approval_status": Find ONLY the approval status for a task. Filters: 'task_title'.
8.  "get_task_timeline": Find ONLY the start and end dates for a task. Filters: 'task_title'.
9.  "get_project_timeline": Find ONLY the start and end dates for a project. Filters: 'project_name'.
10. "get_task_details": Get a comprehensive summary of ALL information for ONE task. Filters: 'task_title'.
11. "get_project_summary": Summarize a project's status. Filters: 'project_name'. (Output: 'visualization').
12. "get_workload_distribution": Show task distribution by project. (No filters). (Output: 'visualization').
13. "get_priority_distribution": Show a breakdown of tasks by priority. (No filters). (Output: 'visualization').
14. "count_tasks": Count tasks. Filters: 'priority', 'status'.
15.  "get_my_tasks_by_date": Find user's tasks due in a timeframe. Filters: 'timeframe', 'priority', 'status'.
16.  "get_upcoming_milestones": List tasks due soon. Filters: 'timeframe', 'priority', 'status'.
17.  "get_long_running_tasks": Find tasks in progress for a while. Filters: 'duration', 'priority'.
18.  "get_my_overdue_with_dependencies": List the user's overdue tasks and dependencies. Filters: 'priority'.
19.  "get_my_skills": Find the user's own skills. No filters.
20.  "get_my_project_team": Find the user's teammates on their projects. No filters.
21.  "get_my_manager": Find the manager(s) associated with the user's tasks. No filters.

RULES:
- A specific question about "skills", "comments", "approvals", or "prerequisites" for a task MUST use the specific intents.
- A general question like "tell me everything" or "give me all details" MUST map to "get_task_details".
- A question about "milestones" MUST use "get_upcoming_milestones".
- A question about "overdue tasks" MUST use "get_my_overdue_with_dependencies".
- A question about tasks "in progress for more than X days" MUST use "get_long_running_tasks".
- A question about tasks due in a specific timeframe (e.g., "next 7 days") MUST use "get_my_tasks_by_date".
- A question about "my skills" MUST use "get_my_skills".
- A question about "my team" or "who I work with" MUST use "get_my_project_team".
- A question about "who is my manager" MUST use "get_my_manager".

- Extract all applicable filters.


- Respond ONLY with the JSON object.

Example 1 (Specific Skills):
User: "what skills for 'Optimize memory usage'?"
Response: {"output_type": "text", "intent": "get_skill_requirements", "filters": {"task_title": "Optimize memory usage"}}

Example 2 (Prerequisites):
User: "what are the prerequisites for 'Optimize memory usage'?"
Response: {"output_type": "text", "intent": "get_prerequisites", "filters": {"task_title": "Optimize memory usage"}}

Example 3 (General Details):
User: "tell me everything about 'Optimize memory usage'"
Response: {"output_type": "text", "intent": "get_task_details", "filters": {"task_title": "Optimize memory usage"}}

Example 4 (Specific Status):
User: "do i have any tasks to do"
Response: {"output_type": "text", "intent": "get_tasks", "filters": {"status": "To Do"}}

Example 5 (Count Query):
User: "how many high priority tasks do I have?"
Response: {"output_type": "text", "intent": "count_tasks", "filters": {"priority": "High"}}

Example 6 (Date with Priority):
User: "Show me my high priority tasks due in the next 7 days"
Response: {"output_type": "text", "intent": "get_my_tasks_by_date", "filters": {"timeframe": "next 7 days", "priority": "High"}}

Example 7 (Overdue with Priority):
User: "List all my high priority overdue tasks and their dependencies"
Response: {"output_type": "text", "intent": "get_my_overdue_with_dependencies", "filters": {"priority": "High"}}

Example 8 (Long-running with Priority):
User: "Which high priority tasks have been in progress for more than 7 days?"
Response: {"output_type": "text", "intent": "get_long_running_tasks", "filters": {"duration": "7 days", "priority": "High"}}

"""

# --- FINAL Text Generation Model ---
summary_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
summary_prompt = """
ROLE: You are Nexus, a helpful assistant.
TASK: Based on the provided JSON data, generate a structured JSON response with "introduction" and "items" keys.
- "introduction": A friendly, one-sentence summary that SPECIFICALLY mentions the context, especially if no results were found.
- "items": An array of strings, formatted as "Key: Value" for dictionaries or simple strings for lists.

RULES:
- If the input data has a "no_results_for" key, your introduction MUST state that no items were found for that specific query.

EXAMPLE (No results for overdue):
Input: {"no_results_for": {"filters": {}, "overdue_tasks": []}}
Response:
{
  "introduction": "You currently have no overdue tasks. Great job!",
  "items": []
}

EXAMPLE (Skills):
Input: {"task_title": "Task A", "required_skills": ["C++"]}
Response:
{
  "introduction": "The following skills are required for the task 'Task A':",
  "items": ["C++"]
}
Now, generate the JSON response for the following data:
"""

def get_intent_from_llm(question: str) -> Dict[str, Any]:
    try:
        full_prompt = f"{intent_prompt}\nUser question: \"{question}\"\nResponse:"
        response = intent_model.generate_content(full_prompt)
        intent_data = json.loads(response.text)
        print(f"AI Service: Received intent from Gemini: {intent_data}")
        return intent_data
    except Exception as e:
        print(f"AI Service ERROR (Intent Extraction): {e}")
        return {"output_type": "text", "intent": "get_tasks", "filters": {}}

def get_text_summary_from_llm(data: Any) -> Dict:
    is_empty = not data or (isinstance(data, dict) and not any(v for k, v in data.items() if k != 'filters'))
    if is_empty:
        context = {"no_results_for": data if isinstance(data, dict) else {}}
        data_json = json.dumps(context)
    else:
        if isinstance(data, dict): data_for_ai = {k: v for k, v in data.items() if v or k == 'filters'}
        else: data_for_ai = data
        data_json = json.dumps(data_for_ai, indent=2)
    try:
        full_prompt = f"{summary_prompt}\n{data_json}"
        response = summary_model.generate_content(full_prompt)
        return json.loads(response.text)
    except Exception as e:
        print(f"AI Service ERROR (Summary Generation): {e}")
        return {"introduction": "I had some trouble summarizing.", "items": []}