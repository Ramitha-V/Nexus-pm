from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

# --- Models for Visualization Data ---
class ChartData(BaseModel):
    chart_type: str  # e.g., 'pie', 'bar'
    title: str
    labels: List[str]
    values: List[int]

# --- Models for Textual Data ---
class TextData(BaseModel):
    introduction: str
    items: List[str] = [] # For bulleted lists

# --- The Main Response Model ---
class ChatAnswer(BaseModel):
    output_type: Literal['text', 'visualization']
    # The 'data' field can be either a ChartData object or a TextData object
    data: Any # Pydantic will validate against the specific type later

class ChatQuery(BaseModel):
    question: str
    user_id: int

class ChatResponse(BaseModel):
    answer: ChatAnswer

