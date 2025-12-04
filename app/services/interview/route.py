from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .services import interviewServicees
from .schema import InterviewQuestion, InterviewResponse
router = APIRouter()

# Initialize the interview service
interview_service = interviewServicees()


@router.post("/interview_round", response_model=InterviewResponse)
async def interview_round(request: InterviewQuestion):
    """
    Submit an interview question and get AI-powered response with EI insights.
    Returns vector database match or AI-generated fallback answer.
    """
    try:
        response_data = interview_service.interview_round(request.question)
        return InterviewResponse(**response_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing interview question: {str(e)}"
        )

@router.post("/load_dataset")
async def load_dataset():
    """
    Load HR interview questions dataset into Pinecone vector database
    """
    try:
        interview_service.process_qa_dataset()
        return {
            "status": "success",
            "message": "Dataset loaded successfully into vector database"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading dataset: {str(e)}"
        )
