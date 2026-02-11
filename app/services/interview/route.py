from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import Optional, List, Any, Union
from .services import interviewServicees
from .schema import (
    InterviewQuestion, 
    InterviewResponse, 
    SnapshotResponse,
    RetrievalStatsResponse,
    TranscriptionResponse
)
import os
import tempfile
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

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

@router.post("/reset_index")
async def reset_index():
    """
    Clear the FAISS index and metadata. Call this before re-loading interview files.
    """
    try:
        result = interview_service.reset_index()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting index: {str(e)}"
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


# =====================================
# VOICE TRANSCRIPTION ENDPOINT (Whisper)
# =====================================

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file (mp3, wav, m4a, webm, mp4, mpeg, mpga, oga, ogg)")
):
    """
    Transcribe an audio file to text using OpenAI Whisper.
    
    Supported formats: mp3, wav, m4a, webm, mp4, mpeg, mpga, oga, ogg
    Max file size: 25MB
    
    Returns the transcribed text that can be used with /generate_strategy endpoint.
    """
    try:
        # Validate file extension
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.webm', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg'}
        file_ext = os.path.splitext(audio_file.filename or "")[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {file_ext}. Supported: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        content = await audio_file.read()
        
        # Check file size (25MB limit for Whisper)
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Audio file too large. Maximum size is 25MB."
            )
        
        # Save to temp file for Whisper API
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Initialize OpenAI client
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Transcribe with Whisper
            with open(temp_file_path, "rb") as audio:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="verbose_json"
                )
            
            logger.info(f"🎤 Transcription complete: {len(transcription.text)} characters")
            
            return TranscriptionResponse(
                status="success",
                transcription=transcription.text,
                language=getattr(transcription, 'language', None),
                duration_seconds=getattr(transcription, 'duration', None),
                confidence=None  # Whisper doesn't provide confidence scores
            )
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error transcribing audio: {str(e)}"
        )


# =====================================
# STRATEGY GENERATION ENDPOINT
# =====================================

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF file."""
    try:
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        return ""


def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract text from uploaded file based on extension."""
    ext = os.path.splitext(filename or "")[1].lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(content)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(content)
    elif ext in ['.txt', '.md', '.text']:
        # Try UTF-8 first, then fallback to latin-1
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            return content.decode('latin-1', errors='ignore')
    else:
        # Try to decode as text
        try:
            return content.decode('utf-8')
        except:
            return ""


@router.post("/generate_strategy", response_model=SnapshotResponse)
async def generate_strategy(
    request: Request,
    challenge_text: str = Form(""),
    context: str = Form(""),
    voice_file: UploadFile = File(None),
    document1: UploadFile = File(None),
    document2: UploadFile = File(None),
    document3: UploadFile = File(None),
    document4: UploadFile = File(None),
    document5: UploadFile = File(None)
):
    """
    Generate a strategic suggestion from multiple input sources.
    
    Accepts:
    - challenge_text: Direct text description of your challenge  
    - context: Additional context information
    - voice_file: Audio file transcribed via Whisper (mp3, wav, m4a, etc.)
    - document1-5: Up to 5 documents (PDF, DOCX, TXT) for additional context
    
    All inputs are optional. Inputs are combined and processed through the EI pipeline 
    to generate strategy snapshots with citations from executive interviews.
    
    Returns the same response format as /interview_round.
    """
    try:
        combined_text_parts = []
        input_sources = []
        
        # 1. Process text input
        if challenge_text and challenge_text.strip():
            combined_text_parts.append(f"Challenge: {challenge_text.strip()}")
            input_sources.append("text")
        
        if context and context.strip():
            combined_text_parts.append(f"Context: {context.strip()}")
            if "text" not in input_sources:
                input_sources.append("text")
        
        # 2. Process voice file (transcribe with Whisper)
        if voice_file and hasattr(voice_file, 'filename') and voice_file.filename:
            allowed_audio_ext = {'.mp3', '.wav', '.m4a', '.webm', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg'}
            voice_ext = os.path.splitext(voice_file.filename or "")[1].lower()
            
            if voice_ext not in allowed_audio_ext:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported audio format: {voice_ext}"
                )
            
            voice_content = await voice_file.read()
            
            if len(voice_content) > 25 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Voice file too large (max 25MB)")
            
            # Transcribe
            with tempfile.NamedTemporaryFile(delete=False, suffix=voice_ext) as temp_file:
                temp_file.write(voice_content)
                temp_path = temp_file.name
            
            try:
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                with open(temp_path, "rb") as audio:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio
                    )
                
                if transcription.text.strip():
                    combined_text_parts.append(f"Voice Input: {transcription.text.strip()}")
                    input_sources.append("voice")
                    logger.info(f"🎤 Voice transcribed: {len(transcription.text)} chars")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # 3. Process document uploads
        document_files = [document1, document2, document3, document4, document5]
        for i, doc in enumerate(document_files, 1):
            # Skip if not a valid UploadFile
            if doc is None or not hasattr(doc, 'filename') or not doc.filename:
                continue
                
            doc_content = await doc.read()
            if not doc_content:
                continue
                
            extracted_text = extract_text_from_file(doc_content, doc.filename)
            
            if extracted_text.strip():
                # Limit document content to avoid token overflow
                max_doc_chars = 5000
                if len(extracted_text) > max_doc_chars:
                    extracted_text = extracted_text[:max_doc_chars] + "... [truncated]"
                
                combined_text_parts.append(f"Document ({doc.filename}): {extracted_text.strip()}")
                if "documents" not in input_sources:
                    input_sources.append("documents")
                logger.info(f"📄 Extracted from {doc.filename}: {len(extracted_text)} chars")
        
        # Validate that we have some input
        if not combined_text_parts:
            raise HTTPException(
                status_code=400,
                detail="No input provided. Please provide challenge text, voice note, or documents."
            )
        
        # 4. Combine all inputs
        combined_input = "\n\n".join(combined_text_parts)
        logger.info(f"📝 Combined input: {len(combined_input)} chars from {input_sources}")
        
        # 5. Run through interview_round
        response_data = interview_service.interview_round(combined_input)
        
        # 6. Return same response as interview_round
        return SnapshotResponse(**response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Strategy generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating strategy: {str(e)}"
        )