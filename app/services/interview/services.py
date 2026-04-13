import os
import json
import faiss
import pickle
from openai import OpenAI
from typing import List, Dict, Any, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import numpy as np
import glob
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OutputClass(Enum):
    """Output classes determined by deterministic gating.
    
    These are decided BEFORE any LLM call based on hard rules.
    LLM scoring cannot upgrade or override these classes.
    EI Contract: REFUSED and FULL_BACKUP short-circuit before LLM generation.
    """
    PRIMARY = "primary"           # High-authority: ≥min thresholds met, bounded insight from evidence
    HYBRID = "hybrid"             # Medium-authority: Partial data, bounded adjacent insight
    FULL_BACKUP = "full_backup"   # Low-authority: Insufficient data, deterministic refusal/reframe
    REFUSED = "refused"           # No authority: Hard refusal, short-circuit before LLM

class SnapshotType(Enum):
    """Types of snapshots based on retrieval results (legacy compatibility)"""
    INTERVIEW_BASED = "interview_based"  # ≥2 chunks
    HYBRID = "hybrid"  # 1 chunk or insufficient insight
    FULL_FALLBACK = "full_fallback"  # 0 chunks - FLAGGED

@dataclass
class GateDecision:
    """Deterministic gate decision made BEFORE LLM call.
    
    This decision is final and cannot be upgraded by LLM scoring.
    """
    output_class: OutputClass
    reason: str
    allow_generation: bool
    chunks_passed: int
    unique_interviews: int
    top_similarity: float
    quality_metrics: Dict[str, Any]

class interviewServicees:
    def __init__(self):
        from app.core.config import settings
        
        # FAISS configuration
        self.index_path = settings.FAISS_INDEX_PATH
        self.metadata_path = f"{self.index_path}_metadata.pkl"
        
        # Initialize OpenAI for embeddings and generation
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL_NAME
        self.embedding_dimension = 3072  # text-embedding-3-large dimension
        self.generation_model = settings.GENERATION_MODEL_NAME
        
        # Confidence threshold for vector search
        self.confidence_threshold = 0.7
        
        # ========================================
        # DETERMINISTIC GATING PARAMETERS (EI)
        # These enforce authority boundaries BEFORE LLM
        # ========================================
        
        # Gate thresholds - these determine output class
        self.GATE_MIN_SIMILARITY_THRESHOLD = 0.30  # Minimum similarity score to consider relevant
        self.GATE_MIN_CHUNK_COUNT_PRIMARY = 2      # Minimum chunks for PRIMARY authority
        self.GATE_MIN_CHUNK_COUNT_HYBRID = 1       # Minimum chunks for HYBRID authority
        self.GATE_MIN_UNIQUE_INTERVIEWS = 2        # Minimum unique interview sources for PRIMARY
        
        # Quality thresholds
        self.GATE_HIGH_QUALITY_THRESHOLD = 0.50    # Score threshold for "high quality" chunk
        
        # Retrieval tracking
        self.retrieval_log = []
        self.min_chunks_for_interview_based = 2  # Legacy - kept for backward compatibility
        self.min_score_for_sufficient_insight = 0.30  # Legacy
        self.min_retrieval_score = 0.15  # Minimum score to consider a chunk relevant
        
        # Initialize FAISS index and metadata
        self.index = None
        self.metadata_store = {}  # Store metadata separately
        self.id_to_index = {}  # Map IDs to FAISS indices
        self.index_to_id = {}  # Map FAISS indices to IDs
        self._setup_index()
    
    def _setup_index(self):
        """Setup FAISS index for EI interview Q&A"""
        try:
            # Try to load existing index
            if os.path.exists(f"{self.index_path}.index") and os.path.exists(self.metadata_path):
                self.index = faiss.read_index(f"{self.index_path}.index")
                with open(self.metadata_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.metadata_store = saved_data['metadata']
                    self.id_to_index = saved_data['id_to_index']
                    self.index_to_id = saved_data['index_to_id']
                print(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner Product (cosine similarity)
                print(f"Created new FAISS index")
            
            print(f"Using embedding model: {self.embedding_model} (dimension: {self.embedding_dimension})")
            
        except Exception as e:
            print(f"Error setting up FAISS index: {e}")
            # Create new index on error
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
    
    def reset_index(self) -> Dict[str, Any]:
        """Reset the FAISS index - clear all vectors and metadata"""
        try:
            old_count = self.index.ntotal
            
            # Create fresh index
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            self.metadata_store = {}
            self.id_to_index = {}
            self.index_to_id = {}
            
            # Delete saved files if they exist
            if os.path.exists(f"{self.index_path}.index"):
                os.remove(f"{self.index_path}.index")
            if os.path.exists(self.metadata_path):
                os.remove(self.metadata_path)
            
            logger.info(f"🗑️ Reset index: cleared {old_count} vectors")
            
            return {
                "status": "success",
                "message": f"Index reset successfully. Cleared {old_count} vectors.",
                "vectors_cleared": old_count
            }
        except Exception as e:
            logger.error(f"Error resetting index: {e}")
            return {"status": "error", "message": str(e)}
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text using OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ EMBEDDING ERROR: {e}")
            logger.error(f"❌ API Key present: {bool(self.openai_client.api_key)}")
            logger.error(f"❌ Model: {self.embedding_model}")
            raise  # Re-raise to surface the error properly
    
    def process_text_files_from_directory(self, directory_path: Optional[str] = None):
        """Process all text files from interview_2 directory and store in FAISS.

        Resolution order for `directory_path`:
        1. Explicit argument
        2. INTERVIEW_FILES_DIR environment variable
        3. project-relative `files/interview_2` (recommended for local runs)
        4. cwd `files/interview_2`
        """
        try:
            if directory_path is None:
                directory_path = (
                    os.getenv("INTERVIEW_FILES_DIR")
                    or str(Path(__file__).resolve().parents[3] / "files" / "interview_2")
                    or str(Path.cwd() / "files" / "interview_2")
                )
            directory_path = os.path.expanduser(str(directory_path))

            # Get all .txt files from the directory
            txt_files = glob.glob(os.path.join(directory_path, "*.txt"))
            
            if not txt_files:
                print(f"No text files found in {directory_path}")
                return {"status": "error", "message": "No text files found"}
            
            vectors_to_add = []
            ids_to_add = []
            metadata_to_add = []
            processed_count = 0
            
            for file_path in txt_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    # Extract metadata from filename and content
                    filename = os.path.basename(file_path)
                    file_id = filename.replace('.txt', '')
                    
                    # Parse the content to extract structured information
                    parsed_data = self._parse_interview_content(content, filename)
                    
                    # Generate embedding for the full content
                    embedding = self.embed_text(content)
                    
                    # Prepare data
                    vector_id = f"interview_{file_id}"
                    metadata = {
                        "filename": filename,
                        "company": parsed_data.get("company", "Unknown"),
                        "role": parsed_data.get("role", "Unknown"),
                        "person": parsed_data.get("person", "Unknown"),
                        "content": content[:1000],  # Store first 1000 chars in metadata
                        "full_text_length": len(content),
                        "type": "ceo_interview",
                        "ei_insights": parsed_data.get("ei_insights", [])
                    }
                    
                    vectors_to_add.append(embedding)
                    ids_to_add.append(vector_id)
                    metadata_to_add.append(metadata)
                    processed_count += 1
                    
                    # Batch add every 50 vectors
                    if len(vectors_to_add) >= 50:
                        self._add_vectors_to_index(vectors_to_add, ids_to_add, metadata_to_add)
                        vectors_to_add = []
                        ids_to_add = []
                        metadata_to_add = []
                        print(f"Processed {processed_count} interview files")
                    
                except Exception as file_error:
                    print(f"Error processing file {file_path}: {file_error}")
                    continue
            
            # Add remaining vectors
            if vectors_to_add:
                self._add_vectors_to_index(vectors_to_add, ids_to_add, metadata_to_add)
            
            # Save index to disk
            self._save_index()
            
            return {
                "status": "success",
                "message": f"Successfully processed {processed_count} interview files",
                "files_processed": processed_count,
                "directory": directory_path,
                "total_vectors": self.index.ntotal
            }
            
        except Exception as e:
            print(f"Error processing text files: {e}")
            return {"status": "error", "message": str(e)}
    
    def _parse_interview_content(self, content: str, filename: str) -> Dict[str, Any]:
        """Parse interview content to extract structured information"""
        lines = content.split('\n')
        parsed = {
            "company": "Unknown",
            "role": "Unknown",
            "person": "Unknown",
            "ei_insights": []
        }
        
        # Extract person name, company, and role from content
        for i, line in enumerate(lines):
            line = line.strip()
            
            if "Company:" in line:
                parsed["company"] = line.split("Company:")[-1].strip()
            elif "Role:" in line:
                parsed["role"] = line.split("Role:")[-1].strip()
            elif i < 10 and len(line) > 3 and len(line) < 50 and line[0].isupper():
                # Likely the person's name in early lines
                if parsed["person"] == "Unknown":
                    parsed["person"] = line
        
        # Extract EI-related insights from content
        ei_keywords = {
            "leadership": ["leadership", "leader", "team", "manage", "motivate"],
            "empathy": ["empathy", "understand", "feelings", "support", "care"],
            "communication": ["communication", "discuss", "talk", "share", "listen"],
            "innovation": ["innovation", "creative", "ideas", "entrepreneurial"],
            "resilience": ["challenge", "overcome", "resilient", "adapt"]
        }
        
        content_lower = content.lower()
        for category, keywords in ei_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                parsed["ei_insights"].append(category)
        
        return parsed
    
    def _categorize_ei_competency(self, question: str, answer: str) -> str:
        """Categorize question/answer into EI competency areas"""
        text = f"{question} {answer}".lower()
        
        competency_keywords = {
            "self_awareness": ["aware", "recognize", "understand yourself", "emotions", "feelings", "self-reflection"],
            "self_regulation": ["manage", "control", "regulate", "stress", "pressure", "difficult situation"],
            "motivation": ["goal", "motivated", "drive", "achievement", "perseverance", "commitment"],
            "empathy": ["understand others", "perspective", "empathy", "feelings of others", "team member"],
            "social_skills": ["communication", "leadership", "conflict", "teamwork", "relationship", "collaborate", "coworker", "disagreement"]
        }
        
        scores = {}
        for competency, keywords in competency_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[competency] = score
        
        return max(scores, key=scores.get) if scores else "general"
    
    def _assess_difficulty(self, question: str) -> str:
        """Assess question difficulty based on complexity"""
        if len(question) < 50:
            return "easy"
        elif len(question) < 100:
            return "medium"
        else:
            return "hard"
    
    def _evaluate_deterministic_gate(self, chunks: List[Dict[str, Any]], user_question: str) -> GateDecision:
        """DETERMINISTIC GATING: Decide output class BEFORE any LLM call.
        
        This is the authority boundary enforcement. The decision made here is FINAL
        and cannot be upgraded by LLM scoring or any other mechanism.
        
        Rules:
        1. Check minimum similarity threshold
        2. Check minimum chunk count
        3. Check unique interview count
        4. Determine output class based on hard thresholds
        
        Returns:
            GateDecision: Final, non-upgradeable decision about output class
        """
        logger.info(f"🚪 DETERMINISTIC GATE: Evaluating {len(chunks)} chunks")
        
        # Filter chunks by minimum similarity threshold
        relevant_chunks = [
            chunk for chunk in chunks 
            if chunk['score'] >= self.GATE_MIN_SIMILARITY_THRESHOLD
        ]
        
        if not relevant_chunks:
            logger.warning(f"❌ GATE DECISION: REFUSED - No chunks meet min similarity {self.GATE_MIN_SIMILARITY_THRESHOLD}")
            return GateDecision(
                output_class=OutputClass.REFUSED,
                reason=f"No chunks meet minimum similarity threshold ({self.GATE_MIN_SIMILARITY_THRESHOLD})",
                allow_generation=False,  # REFUSED short-circuits before any LLM generation
                chunks_passed=0,
                unique_interviews=0,
                top_similarity=chunks[0]['score'] if chunks else 0.0,
                quality_metrics={
                    'total_chunks_retrieved': len(chunks),
                    'chunks_above_threshold': 0,
                    'gate_threshold': self.GATE_MIN_SIMILARITY_THRESHOLD
                }
            )
        
        # Count unique interviews (for CEO interview chunks)
        unique_interviews = set()
        for chunk in relevant_chunks:
            if chunk.get('type') == 'ceo_interview':
                person = chunk.get('person', 'Unknown')
                unique_interviews.add(person)
        
        chunks_passed = len(relevant_chunks)
        unique_interview_count = len(unique_interviews)
        top_similarity = relevant_chunks[0]['score'] if relevant_chunks else 0.0
        
        # Count high-quality chunks
        high_quality_count = sum(
            1 for chunk in relevant_chunks
            if chunk['score'] >= self.GATE_HIGH_QUALITY_THRESHOLD
        )
        
        quality_metrics = {
            'total_chunks_retrieved': len(chunks),
            'chunks_above_threshold': chunks_passed,
            'high_quality_chunks': high_quality_count,
            'unique_interviews': unique_interview_count,
            'top_similarity': top_similarity,
            'gate_similarity_threshold': self.GATE_MIN_SIMILARITY_THRESHOLD,
            'high_quality_threshold': self.GATE_HIGH_QUALITY_THRESHOLD
        }
        
        # DETERMINISTIC DECISION LOGIC
        
        # PRIMARY: High authority - multiple high-quality chunks from diverse sources
        if (chunks_passed >= self.GATE_MIN_CHUNK_COUNT_PRIMARY and 
            unique_interview_count >= self.GATE_MIN_UNIQUE_INTERVIEWS):
            logger.info(f"✅ GATE DECISION: PRIMARY - {chunks_passed} chunks, {unique_interview_count} unique interviews")
            return GateDecision(
                output_class=OutputClass.PRIMARY,
                reason=(f"Met PRIMARY thresholds: {chunks_passed} chunks (≥{self.GATE_MIN_CHUNK_COUNT_PRIMARY}), "
                        f"{unique_interview_count} unique interviews (≥{self.GATE_MIN_UNIQUE_INTERVIEWS})"),
                allow_generation=True,
                chunks_passed=chunks_passed,
                unique_interviews=unique_interview_count,
                top_similarity=top_similarity,
                quality_metrics=quality_metrics
            )
        
        # HYBRID: Medium authority - some data available but below PRIMARY threshold
        elif chunks_passed >= self.GATE_MIN_CHUNK_COUNT_HYBRID:
            logger.info(f"⚠️ GATE DECISION: HYBRID - {chunks_passed} chunks, {unique_interview_count} unique interviews")
            return GateDecision(
                output_class=OutputClass.HYBRID,
                reason=(f"Partial data: {chunks_passed} chunks (≥{self.GATE_MIN_CHUNK_COUNT_HYBRID}), "
                        f"but below PRIMARY threshold ({unique_interview_count} interviews < {self.GATE_MIN_UNIQUE_INTERVIEWS})"),
                allow_generation=True,
                chunks_passed=chunks_passed,
                unique_interviews=unique_interview_count,
                top_similarity=top_similarity,
                quality_metrics=quality_metrics
            )
        
        # FULL_BACKUP: Low authority - insufficient data (deterministic refusal/reframe)
        else:
            logger.warning(f"❌ GATE DECISION: FULL_BACKUP - {chunks_passed} chunks (< {self.GATE_MIN_CHUNK_COUNT_HYBRID})")
            return GateDecision(
                output_class=OutputClass.FULL_BACKUP,
                reason=f"Insufficient data for insight: {chunks_passed} chunks (< {self.GATE_MIN_CHUNK_COUNT_HYBRID}). Deterministic refusal/reframe.",
                allow_generation=False,  # FULL_BACKUP means refuse/reframe, no LLM strategy generation
                chunks_passed=chunks_passed,
                unique_interviews=unique_interview_count,
                top_similarity=top_similarity,
                quality_metrics=quality_metrics
            )
    
    def _mandatory_retrieval(self, user_question: str, top_k: int = 5) -> Dict[str, Any]:
        """MANDATORY retrieval from vector database with comprehensive logging.
        
        This method MUST be called before any snapshot generation.
        Logs retrieval on every request as required.
        """
        retrieval_start = datetime.now()
        
        try:
            # Generate query embedding
            query_embedding = self.embed_text(user_question)
            
            # Normalize for cosine similarity
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Perform vector search
            scores, indices = self.index.search(query_vector, top_k)
            
            # DEBUG: Log raw FAISS results
            logger.info(f"🔎 DEBUG FAISS - Index total: {self.index.ntotal}")
            logger.info(f"🔎 DEBUG FAISS - Raw scores: {scores[0].tolist()}")
            logger.info(f"🔎 DEBUG FAISS - Raw indices: {indices[0].tolist()}")
            logger.info(f"🔎 DEBUG FAISS - index_to_id keys count: {len(self.index_to_id)}")
            logger.info(f"🔎 DEBUG FAISS - min_retrieval_score threshold: {self.min_retrieval_score}")
            
            # Process retrieved chunks
            retrieved_chunks = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty results
                    logger.info(f"🔎 DEBUG: Skipping idx=-1")
                    continue
                
                # Filter out irrelevant chunks with low scores
                if score < self.min_retrieval_score:
                    logger.info(f"🔎 DEBUG: Skipping idx={idx} score={score} (below threshold {self.min_retrieval_score})")
                    continue
                    
                vector_id = self.index_to_id.get(int(idx))
                if not vector_id:
                    logger.info(f"🔎 DEBUG: Skipping idx={idx} - no vector_id found in index_to_id")
                    continue
                    
                metadata = self.metadata_store.get(vector_id, {})
                
                chunk = {
                    "id": vector_id,
                    "score": float(score),
                    "metadata": metadata,
                    "type": metadata.get('type', 'unknown')
                }
                
                # Add type-specific data
                if metadata.get('type') == 'ceo_interview':
                    chunk.update({
                        "company": metadata.get('company', 'Unknown'),
                        "person": metadata.get('person', 'Unknown'),
                        "role": metadata.get('role', 'Unknown'),
                        "content": metadata.get('content', ''),
                        "ei_insights": metadata.get('ei_insights', [])
                    })
                elif metadata.get('type') == 'behavioral_qa':
                    chunk.update({
                        "question": metadata.get('question', ''),
                        "answer": metadata.get('answer', ''),
                        "ei_competency": metadata.get('ei_competency', 'general'),
                        "difficulty": metadata.get('difficulty', 'medium')
                    })
                
                retrieved_chunks.append(chunk)
            
            retrieval_end = datetime.now()
            retrieval_time = (retrieval_end - retrieval_start).total_seconds()
            
            # LOG RETRIEVAL (MANDATORY)
            retrieval_log_entry = {
                "timestamp": retrieval_start.isoformat(),
                "question": user_question,
                "chunks_retrieved": len(retrieved_chunks),
                "top_score": retrieved_chunks[0]['score'] if retrieved_chunks else 0.0,
                "retrieval_time_seconds": retrieval_time,
                "chunk_ids": [chunk['id'] for chunk in retrieved_chunks]
            }
            
            logger.info(f"🔍 RETRIEVAL LOG: {retrieval_log_entry}")
            self.retrieval_log.append(retrieval_log_entry)
            
            return {
                "chunks": retrieved_chunks,
                "total_chunks": len(retrieved_chunks),
                "log_entry": retrieval_log_entry
            }
            
        except Exception as e:
            logger.error(f"❌ RETRIEVAL ERROR: {e}")
            # Even on error, log the retrieval attempt
            error_log = {
                "timestamp": retrieval_start.isoformat(),
                "question": user_question,
                "chunks_retrieved": 0,
                "error": str(e),
                "retrieval_time_seconds": 0.0
            }
            self.retrieval_log.append(error_log)
            
            return {
                "chunks": [],
                "total_chunks": 0,
                "log_entry": error_log,
                "error": str(e)
            }
    
    def search_relevant_answers(self, user_question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Legacy method - maintained for backward compatibility.
        
        WARNING: Use _mandatory_retrieval() for new snapshot system.
        """
        retrieval_result = self._mandatory_retrieval(user_question, top_k)
        return retrieval_result.get('chunks', [])
    
    def _create_interview_based_snapshot(self, user_question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Interview-Based Snapshot from ≥2 retrieved chunks.
        
        Primary intelligence source: Interview dataset.
        AI role: Bounded adjacent insight synthesis only.
        
        CRITICAL: chunks parameter contains ONLY evidence that passed the gate.
        """
        logger.info(f"📊 Creating INTERVIEW-BASED Snapshot from Evidence Pack ({len(chunks)} passed chunks)")
        
        try:
            # Build Evidence Pack from passed chunks only (already filtered by caller)
            interview_context = []
            for i, chunk in enumerate(chunks[:5], 1):  # Use top 5 from Evidence Pack
                if chunk['type'] == 'ceo_interview':
                    interview_context.append(
                        f"[Interview {i}] {chunk['person']} ({chunk['role']} at {chunk['company']}):\n"
                        f"EI Insights: {', '.join(chunk.get('ei_insights', []))}\n"
                        f"Content: {chunk['content']}\n"
                        f"Relevance Score: {chunk['score']:.3f}"
                    )
                elif chunk['type'] == 'behavioral_qa':
                    interview_context.append(
                        f"[Q&A {i}] Q: {chunk['question']}\n"
                        f"A: {chunk['answer']}\n"
                        f"EI Competency: {chunk['ei_competency']}\n"
                        f"Relevance Score: {chunk['score']:.3f}"
                    )
            
            context_str = "\n\n".join(interview_context)
            
            # Synthesis prompt - STRICTLY evidence-based bounded insight
            prompt = f"""You are synthesizing leadership insights from REAL executive interviews to provide bounded adjacent insight.

User Question: {user_question}

EVIDENCE PACK (Passed Gate):
{context_str}

CRITICAL INSTRUCTIONS - VIOLATION WILL RESULT IN FAILURE:
1. ONLY use information explicitly stated in the evidence pack above
2. ABSOLUTELY FORBIDDEN: Adding facts, context, or knowledge about countries, regions, industries, cultures, or situations NOT explicitly mentioned in the evidence
3. If the question mentions specifics (e.g., "in Bangladesh", "in healthcare", "with AI") that are NOT in the evidence:
   - DO NOT attempt to connect the executive's insights to that specific context
   - DO NOT make statements like "In Bangladesh..." or "In the healthcare sector..." 
   - Instead, acknowledge: "The evidence doesn't address [specific context], but executives share these relevant principles..."
4. Synthesize insights from multiple sources when available
5. Cite specific executives/sources when relevant - use their actual words
6. Maintain the authentic voice and wisdom from the evidence
7. If you find yourself typing information you didn't read in the evidence above, STOP
8. Structure the response clearly with key insights
9. Frame as bounded adjacent insight or refusal/reframe based on evidence

Provide a comprehensive response (200-400 words) using ONLY what the evidence contains:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an expert at synthesizing bounded adjacent insights from executive interview evidence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Extract EI competencies from chunks
            ei_competencies = set()
            for chunk in chunks:
                if chunk['type'] == 'ceo_interview':
                    ei_competencies.update(chunk.get('ei_insights', []))
                elif chunk['type'] == 'behavioral_qa':
                    ei_competencies.add(chunk.get('ei_competency', 'general'))
            
            return {
                "status": "success",
                "snapshot_type": SnapshotType.INTERVIEW_BASED.value,
                "question": user_question,
                "answer": response.choices[0].message.content,
                "chunks_used": len(chunks),
                "top_score": chunks[0]['score'] if chunks else 0.0,
                "ei_competencies": list(ei_competencies),
                "sources": [
                    {
                        "type": chunk['type'],
                        "reference": chunk.get('person', chunk.get('question', 'Unknown')[:50]),  # Legacy field
                        "score": chunk['score'],  # Legacy field
                        "interview_id": f"interview_{chunk.get('person', 'unknown').replace(' ', '_').lower()}",
                        "executive_name": chunk.get('person', 'Unknown'),
                        "chunk_id": f"chunk_{i+1}",
                        "similarity_score": chunk['score']
                    } for i, chunk in enumerate(chunks[:3])
                ],
                "confidence_level": "high",
                "retrieval_quality": "excellent"
            }
            
        except Exception as e:
            logger.error(f"Error creating interview-based snapshot: {e}")
            raise
    
    def _create_hybrid_snapshot(self, user_question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Hybrid Snapshot from 1 chunk OR insufficient insight.
        
        Evidence-First: Start with passed chunk(s)
        Bounded Insight: Provide adjacent insight based on evidence only
        
        CRITICAL: chunks parameter contains ONLY evidence that passed the gate.
        """
        logger.info(f"🔀 Creating HYBRID Snapshot from Evidence Pack ({len(chunks)} passed chunks)")
        
        try:
            # Build limited Evidence Pack context
            interview_context = ""
            if chunks:
                chunk = chunks[0]
                if chunk['type'] == 'ceo_interview':
                    interview_context = (
                        f"PARTIAL INTERVIEW INSIGHT:\n"
                        f"Source: {chunk['person']} ({chunk['role']} at {chunk['company']})\n"
                        f"EI Insights: {', '.join(chunk.get('ei_insights', []))}\n"
                        f"Content: {chunk['content']}\n"
                        f"Relevance Score: {chunk['score']:.3f}"
                    )
                elif chunk['type'] == 'behavioral_qa':
                    interview_context = (
                        f"RELATED Q&A:\n"
                        f"Q: {chunk['question']}\n"
                        f"A: {chunk['answer']}\n"
                        f"EI Competency: {chunk['ei_competency']}\n"
                        f"Relevance Score: {chunk['score']:.3f}"
                    )
            
            # Hybrid prompt - Evidence-First, Bounded Adjacent Insight
            prompt = f"""You are creating a HYBRID response using limited evidence to provide bounded adjacent insight.

User Question: {user_question}

{interview_context if interview_context else "NO EVIDENCE AVAILABLE IN PACK"}

CRITICAL INSTRUCTIONS:
1. START with the evidence above (if available) - state what the executive actually said
2. DO NOT fabricate or add details about the executive's context that aren't explicitly mentioned
3. Build upon the executive's wisdom/experience with general frameworks only as bounded adjacent insight
4. You may ONLY provide bounded insight adjacent to the evidence (general principles, universal frameworks, application approaches)
5. DO NOT add specific context about industries, countries, or situations NOT mentioned in the evidence
6. Clearly distinguish between evidence content and bounded adjacent insight
7. If the question asks about specifics not in the evidence, acknowledge: "While the evidence doesn't address [X] specifically, the executive shares relevant principles..."
8. Keep response practical and grounded (150-300 words)
9. Frame as refusal/reframe if evidence is too weak

Provide a hybrid response that honors what was actually in the evidence pack:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an expert at providing bounded adjacent insight based on executive interview evidence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            ei_competencies = []
            if chunks:
                chunk = chunks[0]
                if chunk['type'] == 'ceo_interview':
                    ei_competencies = chunk.get('ei_insights', [])
                elif chunk['type'] == 'behavioral_qa':
                    ei_competencies = [chunk.get('ei_competency', 'general')]
            
            return {
                "status": "success",
                "snapshot_type": SnapshotType.HYBRID.value,
                "question": user_question,
                "answer": response.choices[0].message.content,
                "chunks_used": len(chunks),
                "top_score": chunks[0]['score'] if chunks else 0.0,
                "ei_competencies": ei_competencies,
                "sources": [
                    {
                        "type": chunk['type'],
                        "reference": chunk.get('person', chunk.get('question', 'Unknown')[:50]),  # Legacy field
                        "score": chunk['score'],  # Legacy field
                        "interview_id": f"interview_{chunk.get('person', 'unknown').replace(' ', '_').lower()}",
                        "executive_name": chunk.get('person', 'Unknown'),
                        "chunk_id": f"chunk_{i+1}",
                        "similarity_score": chunk['score']
                    } for i, chunk in enumerate(chunks[:1])
                ] if chunks else [],
                "confidence_level": "medium",
                "retrieval_quality": "partial",
                "note": "Evidence-first response with bounded adjacent insight"
            }
            
        except Exception as e:
            logger.error(f"Error creating hybrid snapshot: {e}")
            raise
    
    # REMOVED: _create_full_fallback_snapshot
    # Per EI contract, FULL_BACKUP must deterministically refuse/reframe, NOT generate with LLM.
    # When output_class="refused" or "full_backup", the system returns deterministically
    # without invoking LLM for strategy generation.
    
    def _generate_fallback_answer(self, user_question: str) -> Dict[str, Any]:
        """Generate answer using OpenAI when no relevant match found"""
        try:
            prompt = f"""
            You are an expert HR interviewer specializing in Emotional Intelligence (EI) assessments. 
            A candidate has asked: "{user_question}"
            
            Provide a comprehensive answer that:
            1. Demonstrates high emotional intelligence
            2. Uses the STAR method (Situation, Task, Action, Result)
            3. Includes EI principles like self-awareness, empathy, and social skills
            4. Is professional and interview-appropriate (150-300 words)
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an expert HR interviewer specializing in Emotional Intelligence."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            ei_competency = self._categorize_ei_competency(user_question, "")
            
            return {
                "answer": response.choices[0].message.content,
                "ei_competency": ei_competency,
                "difficulty": self._assess_difficulty(user_question),
                "source": "AI_generated",
                "confidence_score": 0.85
            }
            
        except Exception as e:
            print(f"Error generating fallback answer: {e}")
            return {
                "answer": "I apologize, but I'm unable to process your question at the moment. Could you please rephrase it?",
                "ei_competency": "general",
                "difficulty": "medium",
                "source": "error_fallback",
                "confidence_score": 0.1
            }
    
    def interview_round(self, user_question: str, enable_llm_scoring: bool = False) -> Dict[str, Any]:
        """Main interview function with DETERMINISTIC GATING enforcement.
        
        CRITICAL FLOW (EI Architecture):
        1. MANDATORY retrieval from vector database (always logged)
        2. DETERMINISTIC GATE evaluation (decides output class BEFORE LLM)
        3. Optional LLM evidence scoring (ONLY if enabled, AFTER gate, CANNOT upgrade class)
        4. Generate snapshot based on gate decision
        5. Return comprehensive response
        
        The gate decision is FINAL and AUDITABLE. LLM cannot override it.
        
        Args:
            user_question: The question to answer
            enable_llm_scoring: If True, run optional LLM scoring AFTER gate (cannot upgrade class)
        
        Returns:
            Dict with snapshot, gate decision, and optional LLM scores
        """
        logger.info(f"🎯 Starting interview_round for question: '{user_question[:100]}...'")
        logger.info(f"🔧 LLM evidence scoring: {'ENABLED' if enable_llm_scoring else 'DISABLED'}")
        
        try:
            # ========================================
            # STEP 1: MANDATORY RETRIEVAL (ALWAYS EXECUTED AND LOGGED)
            # ========================================
            retrieval_result = self._mandatory_retrieval(user_question, top_k=5)
            chunks = retrieval_result['chunks']
            total_chunks = retrieval_result['total_chunks']
            
            logger.info(f"📦 Retrieved {total_chunks} chunks")
            
            # ========================================
            # STEP 2: DETERMINISTIC GATE (AUTHORITY BOUNDARY)
            # This decision is FINAL - made BEFORE any LLM call
            # ========================================
            gate_decision = self._evaluate_deterministic_gate(chunks, user_question)
            
            logger.info(
                f"🚪 GATE DECISION FINAL: {gate_decision.output_class.value.upper()} | "
                f"Reason: {gate_decision.reason}"
            )
            
            # ========================================
            # STEP 3: OPTIONAL LLM EVIDENCE SCORING (POST-GATE ONLY)
            # Can only run AFTER gate decision
            # CANNOT upgrade the class or override refusal
            # ========================================
            llm_evidence_scores = None
            if enable_llm_scoring and gate_decision.allow_generation and gate_decision.chunks_passed > 0:
                logger.info("🤖 Running optional LLM evidence scoring (post-gate)")
                llm_evidence_scores = self._score_evidence_quality_with_llm(
                    user_question, chunks[:gate_decision.chunks_passed]
                )
                logger.info(f"📊 LLM Evidence Scores: {llm_evidence_scores}")
            
            # ========================================
            # STEP 4: GENERATE SNAPSHOT BASED ON GATE DECISION
            # Gate decision determines which generator to use
            # ========================================
            snapshot_response = None
            
            if gate_decision.output_class == OutputClass.PRIMARY:
                # HIGH AUTHORITY - Interview-based snapshot
                # Filter to only chunks that passed the gate
                passed_chunks = [
                    chunk for chunk in chunks 
                    if chunk['score'] >= self.GATE_MIN_SIMILARITY_THRESHOLD
                ][:gate_decision.chunks_passed]
                
                snapshot_response = self._create_interview_based_snapshot(
                    user_question, passed_chunks
                )
                snapshot_response['output_class'] = OutputClass.PRIMARY.value
                
            elif gate_decision.output_class == OutputClass.HYBRID:
                # MEDIUM AUTHORITY - Hybrid snapshot
                passed_chunks = [
                    chunk for chunk in chunks 
                    if chunk['score'] >= self.GATE_MIN_SIMILARITY_THRESHOLD
                ][:gate_decision.chunks_passed]
                
                snapshot_response = self._create_hybrid_snapshot(
                    user_question, passed_chunks
                )
                snapshot_response['output_class'] = OutputClass.HYBRID.value
                
            elif gate_decision.output_class == OutputClass.FULL_BACKUP:
                # LOW AUTHORITY - Deterministic refusal/reframe (NO LLM generation)
                logger.warning("⚠️ FULL_BACKUP: Insufficient evidence for bounded insight - deterministic refusal/reframe")
                snapshot_response = {
                    "status": "refused",
                    "snapshot_type": "full_backup_refusal",
                    "output_class": OutputClass.FULL_BACKUP.value,
                    "question": user_question,
                    "answer": "We cannot provide a bounded insight for this question. The evidence that passed our quality gate is insufficient to generate an authoritative response grounded in the retrieved data.",
                    "chunks_used": gate_decision.chunks_passed,
                    "top_score": gate_decision.top_similarity,
                    "ei_competencies": ["general"],
                    "sources": [],
                    "confidence_level": "insufficient",
                    "retrieval_quality": "below_threshold",
                    "flagged": True,
                    "warning": "⚠️ Insufficient evidence - deterministic refusal/reframe",
                    "recommendation": "Please rephrase your question or provide more context."
                }
                
            elif gate_decision.output_class == OutputClass.REFUSED:
                # NO AUTHORITY - Hard refusal (short-circuit, NO LLM generation)
                logger.error("🚫 REFUSED: No chunks meet minimum similarity - short-circuit before LLM")
                snapshot_response = {
                    "status": "refused",
                    "snapshot_type": "refused",
                    "output_class": OutputClass.REFUSED.value,
                    "question": user_question,
                    "answer": "Unable to provide a response. No evidence in our database meets the minimum relevance threshold for your question.",
                    "chunks_used": 0,
                    "top_score": gate_decision.top_similarity,
                    "ei_competencies": ["general"],
                    "sources": [],
                    "confidence_level": "none",
                    "retrieval_quality": "no_relevant_evidence",
                    "flagged": True,
                    "warning": "⚠️ No relevant evidence found - hard refusal",
                    "recommendation": "Please try rephrasing your question with different keywords."
                }
            
            # ========================================
            # STEP 5: ENRICH RESPONSE WITH GATE METADATA
            # ========================================
            snapshot_response['gate_decision'] = {
                'output_class': gate_decision.output_class.value,
                'reason': gate_decision.reason,
                'chunks_passed_gate': gate_decision.chunks_passed,
                'unique_interviews': gate_decision.unique_interviews,
                'top_similarity': gate_decision.top_similarity,
                'quality_metrics': gate_decision.quality_metrics,
                'is_deterministic': True,  # Flag that this was rule-based
                'gate_timestamp': datetime.now().isoformat()
            }
            
            # Add evidence summary for all responses (EI auditable proof)
            snapshot_response['evidence_summary'] = {
                'chunks_used': snapshot_response.get('chunks_used', 0),
                'unique_interviews': gate_decision.unique_interviews,
                'top_score': snapshot_response.get('top_score', 0.0),
                'similarity_threshold_applied': self.GATE_MIN_SIMILARITY_THRESHOLD,
                'gate_decision': gate_decision.output_class.value
            }
            
            # Add LLM scores if available (but mark as post-gate only)
            if llm_evidence_scores:
                snapshot_response['llm_evidence_scoring'] = {
                    'enabled': True,
                    'scores': llm_evidence_scores,
                    'note': 'LLM scoring performed AFTER gate decision. Cannot upgrade output class.'
                }
            
            # ========================================
            # STEP 6: POST-GENERATION VALIDATION (claim ↔ evidence alignment)
            # ========================================
            if gate_decision.output_class in [OutputClass.PRIMARY, OutputClass.HYBRID]:
                passed_chunks = [
                    chunk for chunk in chunks 
                    if chunk['score'] >= self.GATE_MIN_SIMILARITY_THRESHOLD
                ][:gate_decision.chunks_passed]
                
                validation_result = self._validate_response_against_evidence(
                    snapshot_response.get('answer', ''),
                    passed_chunks,
                    user_question
                )
                
                # ⚡ EI RULE: Auto-downgrade if validation fails
                original_output_class = snapshot_response.get('output_class')
                auto_downgrade_applied = None
                
                if not validation_result.get('validation_passed', True):
                    logger.warning(f"🔻 VALIDATION FAILED - Auto-downgrading from {original_output_class}")
                    
                    if original_output_class == OutputClass.PRIMARY.value:
                        # PRIMARY → HYBRID downgrade
                        snapshot_response['output_class'] = OutputClass.HYBRID.value
                        snapshot_response['snapshot_type'] = SnapshotType.HYBRID.value
                        snapshot_response['confidence_level'] = 'medium'
                        snapshot_response['retrieval_quality'] = 'partial'
                        auto_downgrade_applied = f"PRIMARY → HYBRID (validation failed)"
                        logger.warning("🔻 AUTO-DOWNGRADE: PRIMARY → HYBRID due to validation failure")
                        
                    elif original_output_class == OutputClass.HYBRID.value:
                        # HYBRID → REFUSE downgrade
                        snapshot_response.update({
                            'status': 'refused',
                            'output_class': OutputClass.REFUSED.value,
                            'snapshot_type': 'validation_refusal',
                            'answer': 'Unable to provide a reliable response. Post-generation validation detected issues with evidence alignment.',
                            'confidence_level': 'insufficient',
                            'retrieval_quality': 'validation_failed',
                            'flagged': True,
                            'warning': '⚠️ Validation failure - response refused'
                        })
                        auto_downgrade_applied = f"HYBRID → REFUSED (validation failed)"
                        logger.warning("🔻 AUTO-DOWNGRADE: HYBRID → REFUSED due to validation failure")
                
                
                snapshot_response['validation'] = {
                    'passed': validation_result.get('validation_passed', True),
                    'claims_supported': validation_result.get('claims_verified', 0),
                    'claims_total': validation_result.get('claims_total', 0),
                    'has_generic_language': validation_result.get('has_generic_strategy_language', False),
                    'fabricated_details': validation_result.get('fabricated_details', []),
                    'confidence': validation_result.get('confidence', 'unknown'),
                    'auto_downgrade_applied': auto_downgrade_applied
                }
                
                # Legacy field for backward compatibility
                snapshot_response['post_generation_validation'] = validation_result
            else:
                # Add validation metadata for FULL_BACKUP/REFUSED (no validation performed)
                snapshot_response['validation'] = {
                    'passed': True,  # No validation performed, gate decision was deterministic
                    'claims_supported': 0,
                    'claims_total': 0,
                    'has_generic_language': False,
                    'fabricated_details': [],
                    'confidence': 'not_applicable',
                    'auto_downgrade_applied': None
                }
                snapshot_response['post_generation_validation'] = {
                    'validation_passed': None,
                    'note': 'Not applicable: response was deterministically refused by gate decision before generation.'
                }
            
            # Add retrieval log
            snapshot_response['retrieval_log'] = retrieval_result['log_entry']
            snapshot_response['total_chunks_retrieved'] = total_chunks
            
            # Add competency tips
            if snapshot_response.get('ei_competencies'):
                primary_competency = snapshot_response['ei_competencies'][0]
                snapshot_response['competency_tips'] = self._get_competency_tips(primary_competency)
            
            logger.info(
                f"✅ Snapshot complete: {snapshot_response.get('snapshot_type')} | "
                f"Output Class: {gate_decision.output_class.value} | "
                f"Chunks Passed Gate: {gate_decision.chunks_passed} | "
                f"Confidence: {snapshot_response.get('confidence_level')}"
            )
            
            return snapshot_response
            
        except Exception as e:
            logger.error(f"❌ Error in interview_round: {e}")
            
            # Even on error, ensure retrieval was attempted and logged
            return {
                "status": "error",
                "question": user_question,
                "answer": f"Error processing question: {e}",
                "snapshot_type": "error",
                "output_class": "error",
                "chunks_used": 0,
                "top_score": 0.0,
                "ei_competencies": ["general"],
                "sources": [],
                "confidence_level": "none",
                "retrieval_quality": "error",
                "retrieval_attempted": True,
                "flagged": True,
                "error_details": str(e)
            }
    
    def _validate_response_against_evidence(self, generated_answer: str, chunks: List[Dict[str, Any]], user_question: str) -> Dict[str, Any]:
        """POST-GENERATION VALIDATION: Verify claim ↔ evidence alignment.
        
        This validation checks:
        1. Claims in the response are traceable to evidence chunks
        2. No generic strategy language is present (hallucination indicator)
        3. Citations are properly grounded
        
        Returns:
            Dict with validation results and any flagged issues
        """
        logger.info("🔍 POST-GEN VALIDATION: Checking claim ↔ evidence alignment")
        
        try:
            # Build evidence context for validation
            evidence_context = []
            for i, chunk in enumerate(chunks[:5], 1):
                if chunk['type'] == 'ceo_interview':
                    evidence_context.append(
                        f"Evidence {i}: {chunk.get('person', 'Unknown')} - {chunk.get('content', '')[:500]}"
                    )
                elif chunk['type'] == 'behavioral_qa':
                    evidence_context.append(
                        f"Evidence {i}: {chunk.get('question', '')} | {chunk.get('answer', '')[:300]}"
                    )
            
            evidence_str = "\n\n".join(evidence_context)
            
            # Validation prompt
            validation_prompt = f"""You are a strict fact-checker validating a generated response against source evidence.

QUESTION: {user_question}

SOURCE EVIDENCE:
{evidence_str}

GENERATED RESPONSE:
{generated_answer}

ANALYZE AND RESPOND WITH JSON ONLY:
{{
  "claims_verified": <number of claims that are directly traceable to evidence>,
  "claims_total": <total number of factual claims in response>,
  "has_generic_strategy_language": <true if response contains generic business/leadership advice NOT from evidence>,
  "generic_phrases_found": [<list of generic phrases detected>],
  "evidence_citations_correct": <true if executive names/sources are correctly attributed>,
  "fabricated_details": [<list of any details that appear fabricated/not in evidence>],
  "validation_passed": <true if response is properly grounded>,
  "confidence": <"high"|"medium"|"low">,
  "issues": [<list of specific issues found>]
}}"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are a strict evidence validator. Respond ONLY with valid JSON."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=300
            )
            
            # Parse validation results
            validation_result = json.loads(response.choices[0].message.content)
            
            # Determine if response should be flagged
            validation_result['should_flag'] = (
                validation_result.get('has_generic_strategy_language', False) or
                len(validation_result.get('fabricated_details', [])) > 0 or
                not validation_result.get('validation_passed', True)
            )
            
            logger.info(
                f"🔍 VALIDATION RESULT: passed={validation_result.get('validation_passed')} | "
                f"claims={validation_result.get('claims_verified', 0)}/{validation_result.get('claims_total', 0)} | "
                f"generic_language={validation_result.get('has_generic_strategy_language')}"
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Post-generation validation error: {e}")
            return {
                "validation_passed": None,
                "error": str(e),
                "should_flag": True,
                "note": "Validation failed - manual review recommended"
            }
    
    def _score_evidence_quality_with_llm(self, user_question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """OPTIONAL: Use LLM to score evidence quality AFTER gate decision.
        
        CRITICAL CONSTRAINTS:
        - This runs ONLY after deterministic gate has made its decision
        - Scores are for quality assessment/logging purposes only
        - CANNOT upgrade the output class
        - CANNOT override refusal decisions
        
        Args:
            user_question: The question being answered
            chunks: The chunks that PASSED the deterministic gate
        
        Returns:
            Dict with quality scores for logging/analysis
        """
        logger.info(f"🤖 LLM Evidence Scoring: Evaluating {len(chunks)} chunks (post-gate)")
        
        try:
            # Build context summary for LLM evaluation
            chunk_summaries = []
            for i, chunk in enumerate(chunks[:5], 1):
                if chunk['type'] == 'ceo_interview':
                    chunk_summaries.append(
                        f"Chunk {i}: {chunk.get('person', 'Unknown')} - {chunk.get('role', 'Unknown')} "
                        f"(Similarity: {chunk['score']:.3f})"
                    )
                elif chunk['type'] == 'behavioral_qa':
                    chunk_summaries.append(
                        f"Chunk {i}: Q&A on {chunk.get('ei_competency', 'general')} "
                        f"(Similarity: {chunk['score']:.3f})"
                    )
            
            context_summary = "\n".join(chunk_summaries)
            
            # LLM evaluation prompt
            prompt = f"""You are evaluating the quality of retrieved evidence for a question.

Question: {user_question}

Retrieved Evidence (passed deterministic gate):
{context_summary}

Rate the following on a scale of 1-10:
1. Relevance: How well does the evidence address the question?
2. Diversity: How diverse are the sources/perspectives?
3. Depth: How detailed and substantive is the content?
4. Authoritativeness: How credible are the sources?

Respond ONLY with a JSON object:
{{
  "relevance_score": <1-10>,
  "diversity_score": <1-10>,
  "depth_score": <1-10>,
  "authority_score": <1-10>,
  "overall_quality": <1-10>,
  "brief_assessment": "<1-2 sentence explanation>"
}}"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an evidence quality evaluator. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Parse JSON response
            import json
            scores = json.loads(response.choices[0].message.content)
            
            logger.info(f"📊 LLM Quality Scores: Overall={scores.get('overall_quality', 0)}/10")
            
            return {
                "relevance_score": scores.get("relevance_score", 0),
                "diversity_score": scores.get("diversity_score", 0),
                "depth_score": scores.get("depth_score", 0),
                "authority_score": scores.get("authority_score", 0),
                "overall_quality": scores.get("overall_quality", 0),
                "brief_assessment": scores.get("brief_assessment", ""),
                "note": "These scores are for quality assessment only. They cannot upgrade the output class determined by the deterministic gate."
            }
            
        except Exception as e:
            logger.error(f"❌ Error in LLM evidence scoring: {e}")
            return {
                "error": str(e),
                "note": "LLM scoring failed. Gate decision remains unchanged."
            }
    
    def _get_competency_tips(self, competency: str) -> List[str]:
        """Get tips for specific EI competency"""
        tips = {
            "self_awareness": [
                "Practice mindfulness and self-reflection",
                "Keep a journal of your emotions and reactions",
                "Ask for feedback from trusted colleagues"
            ],
            "self_regulation": [
                "Take deep breaths before reacting",
                "Practice stress management techniques",
                "Set clear boundaries and priorities"
            ],
            "motivation": [
                "Set SMART goals and track progress",
                "Find meaning in your work",
                "Celebrate small wins along the way"
            ],
            "empathy": [
                "Practice active listening",
                "Try to see situations from others' perspectives",
                "Pay attention to non-verbal cues"
            ],
            "social_skills": [
                "Practice clear and open communication",
                "Build rapport with colleagues",
                "Learn conflict resolution techniques"
            ]
        }
        
        return tips.get(competency, ["Continue developing your emotional intelligence skills"])
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the FAISS index"""
        try:
            return {
                "total_vectors": self.index.ntotal,
                "dimension": self.embedding_dimension,
                "metadata_entries": len(self.metadata_store),
                "index_path": self.index_path
            }
        except Exception as e:
            print(f"Error getting index stats: {e}")
            return {}
    
    def _add_vectors_to_index(self, vectors: List[List[float]], ids: List[str], metadata_list: List[Dict[str, Any]]):
        """Add vectors to FAISS index with metadata"""
        try:
            # Convert to numpy array and normalize for cosine similarity
            vectors_array = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors_array)
            
            # Get current index count
            start_idx = self.index.ntotal
            
            # Add vectors to FAISS
            self.index.add(vectors_array)
            
            # Store metadata and ID mappings
            for i, (vector_id, metadata) in enumerate(zip(ids, metadata_list)):
                faiss_idx = start_idx + i
                self.id_to_index[vector_id] = faiss_idx
                self.index_to_id[faiss_idx] = vector_id
                self.metadata_store[vector_id] = metadata
                
        except Exception as e:
            print(f"Error adding vectors to FAISS index: {e}")
            raise
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, f"{self.index_path}.index")
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata_store,
                    'id_to_index': self.id_to_index,
                    'index_to_id': self.index_to_id
                }, f)
            
            print(f"Saved FAISS index with {self.index.ntotal} vectors to {self.index_path}.index")
            
        except Exception as e:
            print(f"Error saving FAISS index: {e}")
    
    def get_retrieval_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent retrieval logs.
        
        Useful for monitoring and auditing retrieval behavior.
        """
        return self.retrieval_log[-limit:]
    
    def get_snapshot_statistics(self) -> Dict[str, Any]:
        """Get statistics about snapshot types generated."""
        if not self.retrieval_log:
            return {
                "total_requests": 0,
                "retrieval_success_rate": 0.0
            }
        
        total_requests = len(self.retrieval_log)
        successful_retrievals = sum(
            1 for log in self.retrieval_log 
            if log.get('chunks_retrieved', 0) > 0
        )
        
        high_quality_retrievals = sum(
            1 for log in self.retrieval_log 
            if log.get('chunks_retrieved', 0) >= 2 and log.get('top_score', 0) >= 0.75
        )
        
        return {
            "total_requests": total_requests,
            "successful_retrievals": successful_retrievals,
            "high_quality_retrievals": high_quality_retrievals,
            "retrieval_success_rate": successful_retrievals / total_requests if total_requests > 0 else 0.0,
            "high_quality_rate": high_quality_retrievals / total_requests if total_requests > 0 else 0.0,
            "zero_chunk_requests": total_requests - successful_retrievals
        }


