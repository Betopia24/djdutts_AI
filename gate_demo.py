#!/usr/bin/env python3
"""Ultra-compact demo - minimal API calls."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from app.services.interview.services import interviewServicees

def show_gate_only():
    """Show deterministic gating without full LLM generation."""
    service = interviewServicees()
    
    print("\n" + "="*60)
    print("DETERMINISTIC GATING DEMO - No LLM Generation")
    print("="*60)
    
    questions = [
        ("PRIMARY", "What insights do CEOs share about leadership and value creation?"),
        ("HYBRID/REFUSE", "How to implement machine learning in pharmaceutical R&D?"),
        ("REFUSE", "Best practices for quantum computing in cryptocurrency mining?")
    ]
    
    for expected, question in questions:
        print(f"\n>>> Testing: {expected}")
        print(f"Q: {question[:60]}...")
        
        # Do retrieval only (no LLM)
        retrieval = service._mandatory_retrieval(question, top_k=5)
        chunks = retrieval['chunks']
        
        # Evaluate gate
        gate = service._evaluate_deterministic_gate(chunks, question)
        
        # Summary
        print(f"   Gate Decision: {gate.output_class.value.upper()}")
        print(f"   Chunks Passed: {gate.chunks_passed}")
        print(f"   Unique Interviews: {gate.unique_interviews}")
        print(f"   Top Similarity: {gate.top_similarity:.3f}")
        print(f"   Allow Generation: {gate.allow_generation}")
        
        if not gate.allow_generation:
            print(f"   ⛔ REFUSED/FULL_BACKUP - No LLM generation would occur")
    
    print("\n" + "="*60)
    print("GATING THRESHOLDS")
    print("="*60)
    print(f"Min Similarity: {service.GATE_MIN_SIMILARITY_THRESHOLD}")
    print(f"Min Chunks (PRIMARY): {service.GATE_MIN_CHUNK_COUNT_PRIMARY}")
    print(f"Min Unique Interviews (PRIMARY): {service.GATE_MIN_UNIQUE_INTERVIEWS}")
    print(f"Min Chunks (HYBRID): {service.GATE_MIN_CHUNK_COUNT_HYBRID}")
    
    print("\nDone!")

if __name__ == "__main__":
    show_gate_only()
