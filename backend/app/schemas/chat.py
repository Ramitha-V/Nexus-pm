from pydantic import BaseModel
from typing import List

class ChatQuery(BaseModel):
    question: str
    user_id: int

class StructuredAnswer(BaseModel):
    introduction: str
    tasks: List[str]

class ChatResponse(BaseModel):
    answer: StructuredAnswer

