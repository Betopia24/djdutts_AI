from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class InterviewQuestion(BaseModel):
    question: str

class SourceReference(BaseModel):
    """Reference to a source chunk used in snapshot generation"""
    type: str
    reference: str
    score: float

class RetrievalLog(BaseModel):
    """Log entry for retrieval operations"""
    timestamp: str
    question: str
    chunks_retrieved: int
    top_score: float
    retrieval_time_seconds: float
    chunk_ids: Optional[List[str]] = None

class SnapshotResponse(BaseModel):
    """Enhanced response model for snapshot-based system"""
    status: str
    snapshot_type: str = Field(
        description="Type: interview_based, hybrid, or full_fallback"
    )
    question: str
    answer: str
    chunks_used: int
    top_score: float
    ei_competencies: List[str]
    sources: List[SourceReference]
    confidence_level: str = Field(
        description="Confidence: high, medium, or low"
    )
    retrieval_quality: str = Field(
        description="Quality: excellent, partial, or none"
    )
    retrieval_log: Optional[Dict[str, Any]] = None
    total_chunks_retrieved: Optional[int] = None
    competency_tips: Optional[List[str]] = None
    flagged: Optional[bool] = Field(
        default=False,
        description="True if full fallback (0 chunks)"
    )
    warning: Optional[str] = None
    note: Optional[str] = None

class InterviewResponse(BaseModel):
    """Legacy response model - maintained for backward compatibility"""
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

class RetrievalStatsResponse(BaseModel):
    """Statistics about retrieval and snapshot generation"""
    total_requests: int
    successful_retrievals: int
    high_quality_retrievals: int
    retrieval_success_rate: float
    high_quality_rate: float
    zero_chunk_requests: int


# =====================================
# Voice & Strategy Endpoint Schemas
# =====================================

class TranscriptionResponse(BaseModel):
    """Response from voice transcription endpoint"""
    status: str
    transcription: str
    language: Optional[str] = None
    duration_seconds: Optional[float] = None
    confidence: Optional[float] = None


class StrategyRequest(BaseModel):
    """Request for strategy generation with optional text input"""
    challenge_text: Optional[str] = Field(
        default=None,
        description="Text description of your challenge or question"
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context for the strategy request"
    )


class StrategyResponse(BaseModel):
    """Response from strategy generation endpoint"""
    status: str
    input_sources: List[str] = Field(
        description="Sources used: text, voice, documents"
    )
    combined_input: str = Field(
        description="The combined text from all input sources"
    )
    snapshot_type: str
    output_class: str
    strategy: str = Field(
        description="The strategic suggestion/answer"
    )
    chunks_used: int
    top_score: float
    sources: List[SourceReference]
    confidence_level: str
    retrieval_quality: str
    ei_competencies: List[str]
    gate_decision: Optional[Dict[str, Any]] = None
    post_generation_validation: Optional[Dict[str, Any]] = None
    flagged: Optional[bool] = False
    warning: Optional[str] = None
    recommendation: Optional[str] = None