from typing import List, Optional
from pydantic import BaseModel

class InterviewQuestion(BaseModel):
    question: str

class InterviewResponse(BaseModel):
    status: str
    question: str
    answer: Optional[str] = None
    confidence_score: Optional[float] = None
    ei_competency: str
    difficulty: Optional[str] = None
    source: Optional[str] = None
    related_questions: Optional[List[str]] = None
    competency_tips: Optional[List[str]] = None
    message: Optional[str] = None