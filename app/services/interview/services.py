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

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SnapshotType(Enum):
    """Types of snapshots based on retrieval results"""
    INTERVIEW_BASED = "interview_based"  # ≥2 chunks
    HYBRID = "hybrid"  # 1 chunk or insufficient insight
    FULL_FALLBACK = "full_fallback"  # 0 chunks - FLAGGED

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
        
        # Retrieval tracking
        self.retrieval_log = []
        self.min_chunks_for_interview_based = 2
        self.min_score_for_sufficient_insight = 0.30  # Adjusted for real-world embedding similarity
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
            print(f"Error generating embedding: {e}")
            return [0.0] * self.embedding_dimension
    
    def process_text_files_from_directory(self, directory_path: str = r"C:\project\djdutts\files\interview_2"):
        """Process all text files from interview_2 directory and store in FAISS"""
        try:
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
    
    def process_qa_dataset(self, json_file_path: str = None):
        """Process and store Q&A dataset in FAISS"""
        try:
            if json_file_path is None:
                json_file_path = r"C:\project\djdutts\files\hr_interview_questions_dataset.json"
            
            if not os.path.exists(json_file_path):
                return {"status": "error", "message": f"File not found: {json_file_path}"}
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                qa_data = json.load(file)
            
            vectors_to_add = []
            ids_to_add = []
            metadata_to_add = []
            
            for i, qa_pair in enumerate(qa_data):
                question = qa_pair.get('question', '')
                answer = qa_pair.get('answer', '')
                
                if not question or not answer:
                    continue
                
                combined_text = f"Question: {question} Answer: {answer}"
                embedding = self.embed_text(combined_text)
                ei_competency = self._categorize_ei_competency(question, answer)
                
                vector_id = f"qa_{i}"
                metadata = {
                    "question": question,
                    "answer": answer,
                    "ei_competency": ei_competency,
                    "difficulty": self._assess_difficulty(question),
                    "type": "behavioral_qa"
                }
                
                vectors_to_add.append(embedding)
                ids_to_add.append(vector_id)
                metadata_to_add.append(metadata)
                
                if len(vectors_to_add) >= 100:
                    self._add_vectors_to_index(vectors_to_add, ids_to_add, metadata_to_add)
                    vectors_to_add = []
                    ids_to_add = []
                    metadata_to_add = []
                    print(f"Processed {i+1} Q&A pairs")
            
            if vectors_to_add:
                self._add_vectors_to_index(vectors_to_add, ids_to_add, metadata_to_add)
            
            # Save index to disk
            self._save_index()
            
            return {
                "status": "success",
                "message": f"Successfully processed {len(qa_data)} Q&A pairs",
                "total_vectors": self.index.ntotal
            }
            
        except Exception as e:
            print(f"Error processing dataset: {e}")
            return {"status": "error", "message": str(e)}
    
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
            
            # Process retrieved chunks
            retrieved_chunks = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty results
                    continue
                
                # Filter out irrelevant chunks with low scores
                if score < self.min_retrieval_score:
                    continue
                    
                vector_id = self.index_to_id.get(int(idx))
                if not vector_id:
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
        AI role: None (pure retrieval-based response).
        """
        logger.info(f"📊 Creating INTERVIEW-BASED Snapshot ({len(chunks)} chunks)")
        
        try:
            # Build context from multiple interview chunks
            interview_context = []
            for i, chunk in enumerate(chunks[:5], 1):  # Use top 5 chunks
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
            
            # Synthesis prompt - STRICTLY interview-based
            prompt = f"""You are synthesizing leadership insights from REAL executive interviews.

User Question: {user_question}

RETRIEVED INTERVIEW INSIGHTS:
{context_str}

CRITICAL INSTRUCTIONS - VIOLATION WILL RESULT IN FAILURE:
1. ONLY use information explicitly stated in the retrieved interviews above
2. ABSOLUTELY FORBIDDEN: Adding facts, context, or knowledge about countries, regions, industries, cultures, or situations NOT explicitly mentioned in the interviews
3. If the question mentions specifics (e.g., "in Bangladesh", "in healthcare", "with AI") that are NOT in the interviews:
   - DO NOT attempt to connect the executive's insights to that specific context
   - DO NOT make statements like "In Bangladesh..." or "In the healthcare sector..." 
   - Instead, acknowledge: "The interviews don't address [specific context], but executives share these relevant principles..."
4. Synthesize insights from multiple sources when available
5. Cite specific executives/sources when relevant - use their actual words
6. Maintain the authentic voice and wisdom from the interviews
7. If you find yourself typing information you didn't read in the interviews above, STOP
8. Structure the response clearly with key insights

Provide a comprehensive response (200-400 words) using ONLY what these executives actually said:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an expert at synthesizing leadership insights from executive interviews."},
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
                        "reference": chunk.get('person', chunk.get('question', 'Unknown')[:50]),
                        "score": chunk['score']
                    } for chunk in chunks[:3]
                ],
                "confidence_level": "high",
                "retrieval_quality": "excellent"
            }
            
        except Exception as e:
            logger.error(f"Error creating interview-based snapshot: {e}")
            raise
    
    def _create_hybrid_snapshot(self, user_question: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Hybrid Snapshot from 1 chunk OR insufficient insight.
        
        Interview-First: Start with retrieved chunk(s)
        AI-Completed: Fill structural gaps only
        """
        logger.info(f"🔀 Creating HYBRID Snapshot ({len(chunks)} chunks - insufficient insight)")
        
        try:
            # Build limited context
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
            
            # Hybrid prompt - Interview-First, AI-Complete structural gaps
            prompt = f"""You are creating a HYBRID response using limited interview data.

User Question: {user_question}

{interview_context if interview_context else "NO INTERVIEW DATA AVAILABLE"}

CRITICAL INSTRUCTIONS:
1. START with the interview insight above (if available) - state what the executive actually said
2. DO NOT fabricate or add details about the executive's context that aren't explicitly mentioned
3. Build upon the executive's wisdom/experience with general frameworks only
4. AI may ONLY complete structural gaps (general examples, universal frameworks, application tips)
5. DO NOT add specific context about industries, countries, or situations NOT mentioned in the interview
6. Clearly distinguish between interview content and supplementary guidance
7. If the question asks about specifics not in the interview, acknowledge: "While the interview doesn't address [X] specifically, the executive shares relevant principles..."
8. Keep response practical and grounded (150-300 words)

Provide a hybrid response that honors what was actually said in the interview:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are an expert at combining interview insights with practical guidance."},
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
                        "reference": chunk.get('person', chunk.get('question', 'Unknown')[:50]),
                        "score": chunk['score']
                    } for chunk in chunks[:1]
                ] if chunks else [],
                "confidence_level": "medium",
                "retrieval_quality": "partial",
                "note": "Interview-first response with AI structural completion"
            }
            
        except Exception as e:
            logger.error(f"Error creating hybrid snapshot: {e}")
            raise
    
    def _create_full_fallback_snapshot(self, user_question: str) -> Dict[str, Any]:
        """Create Full Fallback Snapshot when 0 chunks retrieved.
        
        ⚠️ FLAGGED: No interview data available.
        Pure AI generation - must be clearly marked.
        """
        logger.warning(f"⚠️ Creating FULL FALLBACK Snapshot (0 chunks - FLAGGED)")
        
        try:
            # Fallback prompt with clear warning
            prompt = f"""⚠️ NO INTERVIEW DATA AVAILABLE - PURE AI RESPONSE ⚠️ in our executive database.

User Question: {user_question}

CRITICAL INSTRUCTIONS:
1. Start by clearly stating: "Our executive interview database doesn't contain relevant insights for this question."
2. Provide thoughtful, general business guidance based on best practices
3. Use general frameworks (STAR method, EI principles) when appropriate
4. Keep it professional and business-appropriate
5. DO NOT fabricate executive quotes or specific company examples
6. Acknowledge this is general guidance, not insights from real executives
7. Length: 150-250 words

Provide a helpful, honest0 words

Provide a helpful fallback response:"""
            
            response = self.openai_client.chat.completions.create(
                model=self.generation_model,
                messages=[
                    {"role": "system", "content": "You are a professional interview coach providing general guidance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=350
            )
            
            ei_competency = self._categorize_ei_competency(user_question, "")
            
            return {
                "status": "success",
                "snapshot_type": SnapshotType.FULL_FALLBACK.value,
                "question": user_question,
                "answer": response.choices[0].message.content,
                "chunks_used": 0,
                "top_score": 0.0,
                "ei_competencies": [ei_competency],
                "sources": [],
                "confidence_level": "low",
                "retrieval_quality": "none",
                "flagged": True,
                "warning": "⚠️ No interview data available - pure AI fallback",
                "note": "Consider expanding interview database or refining query"
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback snapshot: {e}")
            raise
    
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
    
    def interview_round(self, user_question: str) -> Dict[str, Any]:
        """Main interview function with MANDATORY retrieval and snapshot logic.
        
        FLOW:
        1. MANDATORY retrieval from vector database (always logged)
        2. Determine snapshot type based on chunks:
           - ≥2 chunks → Interview-Based Snapshot
           - 1 chunk OR insufficient insight → Hybrid Snapshot
           - 0 chunks → Full Fallback Snapshot (FLAGGED)
        3. Generate appropriate snapshot
        4. Return comprehensive response
        
        NO SNAPSHOT MAY BYPASS RETRIEVAL.
        """
        logger.info(f"🎯 Starting interview_round for question: '{user_question[:100]}...'")
        
        try:
            # STEP 1: MANDATORY RETRIEVAL (ALWAYS EXECUTED AND LOGGED)
            retrieval_result = self._mandatory_retrieval(user_question, top_k=5)
            chunks = retrieval_result['chunks']
            total_chunks = retrieval_result['total_chunks']
            
            logger.info(f"📦 Retrieved {total_chunks} chunks")
            
            # STEP 2: DETERMINE SNAPSHOT TYPE
            snapshot_response = None
            
            if total_chunks >= self.min_chunks_for_interview_based:
                # Check if chunks have sufficient insight
                high_quality_chunks = [
                    chunk for chunk in chunks 
                    if chunk['score'] >= self.min_score_for_sufficient_insight
                ]
                
                if len(high_quality_chunks) >= 2:
                    # ≥2 high-quality chunks → INTERVIEW-BASED SNAPSHOT
                    snapshot_response = self._create_interview_based_snapshot(
                        user_question, chunks
                    )
                else:
                    # ≥2 chunks but insufficient quality → HYBRID SNAPSHOT
                    snapshot_response = self._create_hybrid_snapshot(
                        user_question, chunks
                    )
            
            elif total_chunks == 1:
                # 1 chunk → HYBRID SNAPSHOT
                snapshot_response = self._create_hybrid_snapshot(
                    user_question, chunks
                )
            
            else:
                # 0 chunks → FULL FALLBACK SNAPSHOT (FLAGGED)
                snapshot_response = self._create_full_fallback_snapshot(
                    user_question
                )
            
            # STEP 3: ENRICH RESPONSE WITH RETRIEVAL METADATA
            snapshot_response['retrieval_log'] = retrieval_result['log_entry']
            snapshot_response['total_chunks_retrieved'] = total_chunks
            
            # Add competency tips
            if snapshot_response.get('ei_competencies'):
                primary_competency = snapshot_response['ei_competencies'][0]
                snapshot_response['competency_tips'] = self._get_competency_tips(primary_competency)
            
            logger.info(
                f"✅ Snapshot complete: {snapshot_response['snapshot_type']} | "
                f"Chunks: {total_chunks} | Confidence: {snapshot_response.get('confidence_level')}"
            )
            
            return snapshot_response
            
        except Exception as e:
            logger.error(f"❌ Error in interview_round: {e}")
            
            # Even on error, ensure retrieval was attempted and logged
            return {
                "status": "error",
                "question": user_question,
                "message": f"Error processing question: {e}",
                "snapshot_type": "error",
                "ei_competencies": ["general"],
                "retrieval_attempted": True,
                "error_details": str(e)
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


