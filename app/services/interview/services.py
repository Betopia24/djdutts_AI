import os
import json
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
from typing import List, Dict, Any
from app.core.config import settings

class interviewServicees:
    def __init__(self):
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = "ei-interview-qa"
        
        # Initialize Google AI
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
        self.embedding_model = "models/embedding-001"
        self.generation_model = "gemini-pro"
        
        # Confidence threshold for vector search
        self.confidence_threshold = 0.7  # If similarity score < 0.7, use fallback
        
        # Initialize index
        self.index = None
        self._setup_index()
    
    def _setup_index(self):
        """Setup Pinecone index for EI interview Q&A"""
        try:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                # Create index with 768 dimensions (for Google embedding-001)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=768,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            
            self.index = self.pc.Index(self.index_name)
            print(f"Connected to index: {self.index_name}")
            
        except Exception as e:
            print(f"Error setting up index: {e}")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for text using Google AI"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return [0.0] * 768  # Return zero vector on error
    def process_qa_dataset(self, json_file_path: str = None):
        """Process and store Q&A dataset in Pinecone"""
        try:
            # Use the default path if none provided
            if json_file_path is None:
                json_file_path = "files/hr_interview_questions_dataset.json"
            
            if not os.path.exists(json_file_path):
                raise FileNotFoundError(f"Dataset file not found: {json_file_path}")
            
            with open(json_file_path, 'r', encoding='utf-8') as file:
                qa_data = json.load(file)
            
            vectors_to_upsert = []
            
            for i, qa_pair in enumerate(qa_data):
                question = qa_pair.get('question', '')
                answer = qa_pair.get('answer', '')
                
                # Skip empty entries
                if not question or not answer:
                    continue
                
                # Combine question and answer for better context
                combined_text = f"Question: {question} Answer: {answer}"
                
                # Generate embedding using Google AI
                embedding = self.embed_text(combined_text)
                
                # Determine EI competency (basic categorization)
                ei_competency = self._categorize_ei_competency(question, answer)
                
                # Prepare vector data
                vector_data = {
                    "id": f"qa_{i}",
                    "values": embedding,
                    "metadata": {
                        "question": question,
                        "answer": answer,
                        "ei_competency": ei_competency,
                        "difficulty": self._assess_difficulty(question),
                        "type": "behavioral_qa"
                    }
                }
                
                vectors_to_upsert.append(vector_data)
                
                # Batch upsert every 100 vectors
                if len(vectors_to_upsert) >= 100:
                    self.index.upsert(vectors_to_upsert)
                    vectors_to_upsert = []
                    print(f"Processed {i+1} Q&A pairs")
            
            # Upsert remaining vectors
            if vectors_to_upsert:
                self.index.upsert(vectors_to_upsert)
            
            print(f"Successfully processed {len(qa_data)} Q&A pairs")
            
        except Exception as e:
            print(f"Error processing dataset: {e}")
    
    def _categorize_ei_competency(self, question: str, answer: str) -> str:
        """Categorize question/answer into EI competency areas"""
        text = f"{question} {answer}".lower()
        
        # EI competency keywords mapping
        competency_keywords = {
            "self_awareness": ["aware", "recognize", "understand yourself", "emotions", "feelings", "self-reflection", "weakness", "strength"],
            "self_regulation": ["manage", "control", "regulate", "stress", "pressure", "difficult situation", "handle", "cope"],
            "motivation": ["goal", "motivated", "drive", "achievement", "perseverance", "commitment", "challenge", "overcome"],
            "empathy": ["understand others", "perspective", "empathy", "feelings of others", "team member", "coworker", "colleague"],
            "social_skills": ["communication", "leadership", "conflict", "teamwork", "relationship", "collaborate", "resolved", "disagreement", "negotiate"]
        }
        
        scores = {}
        for competency, keywords in competency_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[competency] = score
        
        # Return competency with highest score
        return max(scores, key=scores.get) if scores else "general"
    
    def _assess_difficulty(self, question: str) -> str:
        """Assess question difficulty based on complexity"""
        if len(question) < 50:
            return "easy"
        elif len(question) < 100:
            return "medium"
        else:
            return "hard"
    
    def search_relevant_answers(self, user_question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant answers using vector similarity"""
        try:
            # Generate embedding for user question using Google AI
            query_embedding = self.embed_text(user_question)
            
            # Search in Pinecone
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            # Format results
            relevant_answers = []
            for match in search_results['matches']:
                result = {
                    "score": match['score'],
                    "question": match['metadata']['question'],
                    "answer": match['metadata']['answer'],
                    "ei_competency": match['metadata']['ei_competency'],
                    "difficulty": match['metadata']['difficulty']
                }
                relevant_answers.append(result)
            
            return relevant_answers
            
        except Exception as e:
            print(f"Error searching for answers: {e}")
            return []
    
    def _generate_fallback_answer(self, user_question: str) -> Dict[str, Any]:
        """Generate answer using Gemini when no relevant match found in vector DB"""
        try:
            model = genai.GenerativeModel(self.generation_model)
            
            # Create a comprehensive prompt for EI interview response
            prompt = f"""
            You are an expert HR interviewer specializing in Emotional Intelligence (EI) assessments. 
            A candidate has asked the following interview question: "{user_question}"
            
            Please provide:
            1. A comprehensive, professional answer that demonstrates high emotional intelligence
            2. Focus on behavioral examples and STAR method (Situation, Task, Action, Result)
            3. Include emotional intelligence principles like self-awareness, empathy, and social skills
            4. Make it realistic and actionable
            
            Keep the response professional, concise (150-300 words), and interview-appropriate.
            """
            
            response = model.generate_content(prompt)
            
            # Check if response was generated successfully
            if not response or not response.text:
                raise Exception("No response generated from AI model")
            
            # Determine EI competency from the question
            ei_competency = self._categorize_ei_competency(user_question, "")
            
            return {
                "answer": response.text.strip(),
                "ei_competency": ei_competency,
                "difficulty": self._assess_difficulty(user_question),
                "source": "AI_generated",
                "confidence_score": 0.85  # Moderate confidence for AI-generated
            }
            
        except Exception as e:
            print(f"Error generating fallback answer: {e}")
            # Provide a more helpful static response based on question type
            ei_competency = self._categorize_ei_competency(user_question, "")
            
            static_responses = {
                "self_awareness": "Focus on describing a specific situation where you recognized your emotions and how they impacted your work. Use the STAR method (Situation, Task, Action, Result) to structure your response.",
                "self_regulation": "Describe a challenging situation where you had to manage your emotions effectively. Explain the techniques you used and the positive outcome.",
                "motivation": "Share an example where you overcame obstacles to achieve a goal. Highlight your persistence and what drives you to succeed.",
                "empathy": "Describe a time when you helped a colleague or understood their perspective. Show how you recognized their emotions and responded appropriately.",
                "social_skills": "Explain a situation where you successfully collaborated with others or resolved a conflict. Focus on your communication and relationship-building skills."
            }
            
            fallback_answer = static_responses.get(
                ei_competency, 
                "Please provide a specific example from your experience. Use the STAR method: describe the Situation, Task, Action you took, and Result achieved."
            )
            
            return {
                "answer": fallback_answer,
                "ei_competency": ei_competency,
                "difficulty": self._assess_difficulty(user_question),
                "source": "static_fallback",
                "confidence_score": 0.6
            }
    

    def interview_round(self, user_question: str) -> Dict[str, Any]:
        """Main interview function - returns relevant answer with EI context + fallback"""
        try:
            # Search for relevant answers in vector database
            relevant_answers = self.search_relevant_answers(user_question, top_k=3)
            
            # Check if we have good matches above confidence threshold
            if relevant_answers and relevant_answers[0]['score'] >= self.confidence_threshold:
                # Use vector database result
                best_match = relevant_answers[0]
                
                response = {
                    "status": "success",
                    "question": user_question,
                    "answer": best_match['answer'],
                    "confidence_score": best_match['score'],
                    "ei_competency": best_match['ei_competency'],
                    "difficulty": best_match['difficulty'],
                    "source": "vector_database",
                    "related_questions": [qa['question'] for qa in relevant_answers[1:3]],
                    "competency_tips": self._get_competency_tips(best_match['ei_competency'])
                }
                
            else:
                # Use fallback AI generation
                print(f"No high-confidence match found. Using AI fallback for: {user_question}")
                fallback_result = self._generate_fallback_answer(user_question)
                
                response = {
                    "status": "success",
                    "question": user_question,
                    "answer": fallback_result['answer'],
                    "confidence_score": fallback_result['confidence_score'],
                    "ei_competency": fallback_result['ei_competency'],
                    "difficulty": fallback_result['difficulty'],
                    "source": fallback_result['source'],
                    "related_questions": [],  # No related questions for AI-generated
                    "competency_tips": self._get_competency_tips(fallback_result['ei_competency'])
                }
            
            return response
            
        except Exception as e:
            return {
                "status": "error",
                "question": user_question,
                "message": f"Error processing question: {e}",
                "ei_competency": "general",
                "source": "error"
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


