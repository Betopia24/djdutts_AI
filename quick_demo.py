#!/usr/bin/env python3
"""Compact demo showing all three EI cases."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.services.interview.services import interviewServicees

def run_demo():
    service = interviewServicees()
    print("\n" + "="*70)
    print("EVIDENCE INTELLIGENCE DEMO - THREE CASES")
    print("="*70)
    
    # CASE 1: PRIMARY
    print("\n>>> CASE 1: Strong Evidence (Expected: PRIMARY)")
    print("-"*50)
    q1 = "What insights do CEOs share about building trust and creating value?"
    r1 = service.interview_round(q1)
    gate1 = r1.get("gate_decision", {})
    print(f"Gate Decision: {gate1.get('output_class', 'N/A').upper()}")
    print(f"Chunks Used: {r1.get('chunks_used', 0)} | Unique Interviews: {gate1.get('unique_interviews', 0)}")
    print(f"Top Score: {r1.get('top_score', 0):.3f}")
    print(f"Citations: {[s.get('reference')[:30] for s in r1.get('sources', [])]}")
    print(f"Snapshot Type: {r1.get('snapshot_type')}")
    if r1.get('post_generation_validation'):
        pv = r1['post_generation_validation']
        print(f"Post-Gen Validation: passed={pv.get('validation_passed')} claims={pv.get('claims_verified')}/{pv.get('claims_total')}")
    
    # CASE 2: HYBRID 
    print("\n>>> CASE 2: Partial Evidence (Expected: HYBRID)")
    print("-"*50)
    # Question that should match some content but with limited sources
    q2 = "What strategies do leaders use to leverage AI and advanced technology?"
    r2 = service.interview_round(q2)
    gate2 = r2.get("gate_decision", {})
    print(f"Gate Decision: {gate2.get('output_class', 'N/A').upper()}")
    print(f"Chunks Used: {r2.get('chunks_used', 0)} | Unique Interviews: {gate2.get('unique_interviews', 0)}")
    print(f"Top Score: {r2.get('top_score', 0):.3f}")
    print(f"Snapshot Type: {r2.get('snapshot_type')}")
    
    # CASE 3: REFUSE
    print("\n>>> CASE 3: No Evidence (Expected: REFUSE/FULL_BACKUP)")
    print("-"*50)
    q3 = "What are best practices for quantum computing in cryptocurrency mining?"
    r3 = service.interview_round(q3)
    gate3 = r3.get("gate_decision", {})
    print(f"Gate Decision: {gate3.get('output_class', 'N/A').upper()}")
    print(f"Status: {r3.get('status')} | Flagged: {r3.get('flagged')}")
    print(f"Top Score: {r3.get('top_score', 0):.3f}")
    print(f"Answer Preview: {r3.get('answer', '')[:100]}...")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Case 1: {gate1.get('output_class', 'N/A').upper()} - {r1.get('chunks_used', 0)} chunks from {gate1.get('unique_interviews', 0)} interviews")
    print(f"Case 2: {gate2.get('output_class', 'N/A').upper()} - {r2.get('chunks_used', 0)} chunks from {gate2.get('unique_interviews', 0)} interviews")
    print(f"Case 3: {gate3.get('output_class', 'N/A').upper()} - Flagged={r3.get('flagged')} (deterministic refusal)")
    
    print("\nDone!")

if __name__ == "__main__":
    run_demo()
