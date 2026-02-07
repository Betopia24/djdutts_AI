from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .services import interviewServicees
from .schema import (
    InterviewQuestion, 
    InterviewResponse, 
    SnapshotResponse,
    RetrievalStatsResponse
)

router = APIRouter()

# Initialize the interview service
interview_service = interviewServicees()


@router.post("/interview_round", response_model=SnapshotResponse)
async def interview_round(request: InterviewQuestion):
    """
    Submit an interview question and get snapshot-based response with MANDATORY retrieval.
    
    Snapshot Types:
    - Interview-Based (≥2 chunks): Pure interview insights
    - Hybrid (1 chunk/insufficient): Interview-first, AI-completed
    - Full Fallback (0 chunks): AI-only, FLAGGED
    
    Every request includes retrieval logging for audit purposes.
    """
    try:
        response_data = interview_service.interview_round(request.question)
        return SnapshotResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing interview question: {str(e)}"
        )

@router.post("/load_qa_dataset")
async def load_qa_dataset():
    """
    Load the HR interview questions JSON dataset into Pinecone
    
    NOTE: This endpoint requires hr_interview_questions_dataset.json file to exist in files/ directory
    """
    try:
        result = interview_service.process_qa_dataset()
        return result
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading Q&A dataset: {str(e)}"
        )

@router.post("/load_interview_files")
async def load_interview_files():
    """
    Load CEO interview text files from interview_2 directory into Pinecone
    """
    try:
        result = interview_service.process_text_files_from_directory()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading interview files: {str(e)}"
        )

@router.get("/stats")
async def get_stats():
    """
    Get Pinecone index statistics
    """
    try:
        stats = interview_service.get_index_stats()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )

@router.get("/retrieval_logs")
async def get_retrieval_logs(limit: int = 10):
    """
    Get recent retrieval logs for monitoring and audit.
    Shows all retrieval attempts with chunk counts and scores.
    """
    try:
        logs = interview_service.get_retrieval_logs(limit)
        return {
            "status": "success",
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting retrieval logs: {str(e)}"
        )

@router.get("/snapshot_statistics", response_model=RetrievalStatsResponse)
async def get_snapshot_statistics():
    """
    Get statistics about snapshot generation and retrieval quality.
    
    Metrics include:
    - Total requests processed
    - Successful retrievals (>0 chunks)
    - High-quality retrievals (≥2 chunks, score ≥0.75)
    - Success rates
    - Zero-chunk (fallback) requests
    """
    try:
        stats = interview_service.get_snapshot_statistics()
        return RetrievalStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting snapshot statistics: {str(e)}"
        )
