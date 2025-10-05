from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

# --- Model for Visualization Data ---
class ChartData(BaseModel):
    chart_type: str  # e.g., 'pie', 'bar'
    title: str
    labels: List[str]
    values: List[int]

# --- Model for Textual Data ---
class TextData(BaseModel):
    introduction: str
    items: List[str] = []

# --- The Main Response Model ---
class ManagerChatAnswer(BaseModel):
    output_type: Literal['text', 'visualization']
    # The 'data' field can be either a ChartData or a TextData object
    data: Any

class ManagerChatQuery(BaseModel):
    question: str
    manager_id: int

class ManagerChatResponse(BaseModel):
    answer: ManagerChatAnswer