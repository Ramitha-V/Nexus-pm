import google.generativeai as genai
import json
from typing import List, Dict, Any
from app.core.config import settings

# Configure the Gemini API client
genai.configure(api_key=settings.GEMINI_API_KEY)

generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
MODEL_NAME = 'gemini-2.5-flash' # Or your working model name

# --- Updated AI Model for Intent Recognition ---
filter_model = genai.GenerativeModel(MODEL_NAME, generation_config=generation_config)
filter_prompt = """
Your only job is to analyze the user's question and generate a JSON object describing their intent.

You can identify three types of intents:
1.  "get_tasks": For questions about finding tasks based on status or priority.
2.  "get_overdue": For questions about late or overdue tasks.
3.  "get_dependencies": For questions about prerequisites. For this intent, you MUST also extract the task title from the user's query.

The JSON output must have an "intent" key and a "filters" key.

- For "get_tasks", the filters can be 'priority' and 'status'.
- For "get_overdue", the filters can include 'priority'.
- For "get_dependencies", the filters MUST include 'task_title'.

Respond ONLY with a valid JSON object.

Example 1 (Get Tasks):
User: "what are my high priority tasks"
Response: {"intent": "get_tasks", "filters": {"priority": "High"}}

Example 2 (Get Overdue):
User: "show me my overdue tasks"
Response: {"intent": "get_overdue", "filters": {}}

Example 3 (Get Dependencies):
User: "what are the prerequisites for 'Optimize the rendering pipeline'"
Response: {"intent": "get_dependencies", "filters": {"task_title": "Optimize the rendering pipeline"}}
"""

# --- Updated AI Model for Summaries ---
summary_model = genai.GenerativeModel(MODEL_NAME) # This one returns text
summary_prompt = """
You are Nexus, a helpful project management assistant. Based ONLY on the provided JSON data, 
provide a friendly and concise summary in natural language.

- If the data contains a list of tasks, format them as a Markdown bulleted list. Each item MUST be on a new line.
- If the data is about dependencies, explain them clearly (e.g., "To start 'Task A', you first need to complete the following: ...").
- If there is no data or the list is empty, say so in a friendly way.

Here is the data:
"""

def get_intent_from_llm(question: str) -> Dict[str, Any]:
    """Analyzes the user's question to determine their intent and any filters."""
    try:
        full_prompt = f"{filter_prompt}\nUser question: \"{question}\"\nResponse:"
        response = filter_model.generate_content(full_prompt)
        intent_data = json.loads(response.text)
        print(f"AI Service: Received intent from Gemini: {intent_data}")
        return intent_data
    except Exception as e:
        print(f"AI Service ERROR (Intent Extraction): {e}")
        return {"intent": "get_tasks", "filters": {}} # Default fallback

def get_natural_language_summary_from_llm(data: Any) -> str:
    """Generates a friendly summary for any kind of data (tasks, dependencies, etc.)."""
    # Check for empty lists in the data
    if not data or (isinstance(data, dict) and "dependencies" in data and not data["dependencies"]):
        return "It looks like there are no items that match your request, or the specified task has no prerequisites."
    try:
        data_json = json.dumps(data, indent=2)
        full_prompt = f"{summary_prompt}\n{data_json}"
        response = summary_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        print(f"AI Service ERROR (Summary Generation): {e}")
        return "I had a bit of trouble generating a summary, but here is the raw data: " + str(data)

