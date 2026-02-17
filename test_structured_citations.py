#!/usr/bin/env python3
"""
Test Script: Structured Citation Metadata Validation 

This script validates the new structured citation metadata format for EI intelligence layer.
Tests both PRIMARY (multi-interview) and FULL_BACKUP (no relevant chunks) examples.
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.interview.services import interviewServicees


def print_structured_citations(response: dict):
    """Print structured citation metadata in a formatted way."""
    print(f"\n📖 Structured Citation Metadata:")
    sources = response.get('sources', [])
    
    if not sources:
        print(f"   No citations (sources empty - expected for FULL_BACKUP/REFUSED)")
        return
        
    for i, source in enumerate(sources, 1):
        print(f"   Citation {i}:")
        print(f"   ├─ Interview ID: {source.get('interview_id', 'N/A')}")
        print(f"   ├─ Executive Name: {source.get('executive_name', 'N/A')}")
        print(f"   ├─ Chunk ID: {source.get('chunk_id', 'N/A')}")
        print(f"   ├─ Similarity Score: {source.get('similarity_score', 0.0):.3f}")
        print(f"   └─ Source Type: {source.get('type', 'N/A')}")


def test_primary_example():
    """Test PRIMARY example with ≥2 interviews, ≥2 chunks."""
    print("=" * 80)
    print("🎯 TESTING PRIMARY EXAMPLE")
    print("=" * 80)
    print("Query: How do successful leaders approach building innovative teams?")
    
    try:
        service = interviewServicees()
        response = service.interview_round(
            "How do successful leaders approach building innovative teams and managing organizational change?"
        )
        
        # Display core response info
        print(f"\n📊 Core Response Details:")
        print(f"   ├─ Status: {response.get('status')}")
        print(f"   ├─ Snapshot Type: {response.get('snapshot_type')}")
        print(f"   ├─ Output Class: {response.get('output_class', 'N/A')}")
        print(f"   ├─ Chunks Used: {response.get('chunks_used', 0)}")
        print(f"   ├─ Top Score: {response.get('top_score', 0.0):.3f}")
        print(f"   └─ Confidence Level: {response.get('confidence_level')}")
        
        # Gate Decision info
        gate_decision = response.get('gate_decision', {})
        print(f"\n⚡ Gate Decision:")
        print(f"   ├─ Output Class: {gate_decision.get('output_class')}")
        print(f"   ├─ Chunks Passed: {gate_decision.get('chunks_passed_gate')}")
        print(f"   ├─ Unique Interviews: {gate_decision.get('unique_interviews')}")
        print(f"   └─ Reason: {gate_decision.get('reason', 'N/A')}")
        
        # Structured citations (the new feature!)
        print_structured_citations(response)
        
        # Answer preview
        answer = response.get('answer', '')
        print(f"\n📝 Answer Preview (first 200 chars):")
        print(f"   {answer[:200]}...")
        
        # Validation checks
        print(f"\n✅ Validation Checks:")
        chunks_used = response.get('chunks_used', 0)
        unique_interviews = gate_decision.get('unique_interviews', 0)
        sources_count = len(response.get('sources', []))
        
        print(f"   ├─ Chunks Used ≥ 2: {'✅' if chunks_used >= 2 else '❌'} ({chunks_used} chunks)")
        print(f"   ├─ Unique Interviews ≥ 2: {'✅' if unique_interviews >= 2 else '❌'} ({unique_interviews} interviews)")
        print(f"   ├─ Has Citations: {'✅' if sources_count > 0 else '❌'} ({sources_count} sources)")
        print(f"   ├─ Primary Snapshot: {'✅' if response.get('snapshot_type') == 'interview_based' else '❌'}")
        print(f"   └─ Structured Metadata: {'✅' if sources_count > 0 and 'interview_id' in response.get('sources', [{}])[0] else '❌'}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error testing PRIMARY example: {e}")
        return None


def test_full_backup_example():
    """Test FULL_BACKUP example with no relevant chunks."""
    print("\n" + "=" * 80)
    print("🛑 TESTING FULL_BACKUP EXAMPLE")
    print("=" * 80)
    print("Query: Completely unrelated question to force FULL_BACKUP")
    
    try:
        service = interviewServicees()
        response = service.interview_round(
            "What is the atomic weight of plutonium in quantum mechanics?"
        )
        
        # Display core response info
        print(f"\n📊 Core Response Details:")
        print(f"   ├─ Status: {response.get('status')}")
        print(f"   ├─ Snapshot Type: {response.get('snapshot_type')}")
        print(f"   ├─ Output Class: {response.get('output_class', 'N/A')}")
        print(f"   ├─ Chunks Used: {response.get('chunks_used', 0)}")
        print(f"   ├─ Top Score: {response.get('top_score', 0.0):.3f}")
        print(f"   ├─ Confidence Level: {response.get('confidence_level')}")
        print(f"   └─ Flagged: {response.get('flagged', False)}")
        
        # Gate Decision info
        gate_decision = response.get('gate_decision', {})
        print(f"\n⚡ Gate Decision:")
        print(f"   ├─ Output Class: {gate_decision.get('output_class')}")
        print(f"   ├─ Chunks Passed: {gate_decision.get('chunks_passed_gate')}")
        print(f"   ├─ Allow Generation: {gate_decision.get('allow_generation')}")
        print(f"   └─ Reason: {gate_decision.get('reason', 'N/A')}")
        
        # Structured citations (should be empty)
        print_structured_citations(response)
        
        # Answer preview
        answer = response.get('answer', '')
        print(f"\n📝 Answer Preview:")
        print(f"   {answer}")
        
        # Warning
        warning = response.get('warning', '')
        if warning:
            print(f"\n⚠️  Warning: {warning}")
        
        # Validation checks
        print(f"\n✅ Validation Checks:")
        chunks_used = response.get('chunks_used', 0)
        sources_count = len(response.get('sources', []))
        is_flagged = response.get('flagged', False)
        output_class = response.get('output_class', '')
        
        print(f"   ├─ Zero Chunks: {'✅' if chunks_used == 0 else '❌'} ({chunks_used} chunks)")
        print(f"   ├─ No Sources: {'✅' if sources_count == 0 else '❌'} ({sources_count} sources)")
        print(f"   ├─ Flagged: {'✅' if is_flagged else '❌'} (flagged={is_flagged})")
        print(f"   ├─ No Authoritative Language: {'✅' if 'unable' in answer.lower() or 'cannot' in answer.lower() else '❌'}")
        print(f"   └─ FULL_BACKUP/REFUSED Class: {'✅' if output_class in ['full_backup', 'refused'] else '❌'} ({output_class})")
        
        return response
        
    except Exception as e:
        print(f"❌ Error testing FULL_BACKUP example: {e}")
        return None


def show_json_output_sample(response: dict, title: str):
    """Show a clean JSON sample of the response."""
    print(f"\n" + "=" * 80)
    print(f"🔍 JSON OUTPUT SAMPLE: {title}")
    print("=" * 80)
    
    # Create a clean sample showing key structured citation fields
    sample = {
        "status": response.get('status'),
        "snapshot_type": response.get('snapshot_type'),
        "output_class": response.get('output_class'),
        "chunks_used": response.get('chunks_used'),
        "sources": response.get('sources', []),
        "gate_decision": {
            "output_class": response.get('gate_decision', {}).get('output_class'),
            "chunks_passed_gate": response.get('gate_decision', {}).get('chunks_passed_gate'),
            "unique_interviews": response.get('gate_decision', {}).get('unique_interviews'),
            "reason": response.get('gate_decision', {}).get('reason')
        }
    }
    
    print(json.dumps(sample, indent=2))


def main():
    """Main test runner."""
    print("🧪 STRUCTURED CITATION METADATA TESTING")
    print("Testing enhanced JSON responses with structured citation data")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: PRIMARY example
    primary_response = test_primary_example()
    if primary_response:
        show_json_output_sample(primary_response, "PRIMARY EXAMPLE")
    
    # Test 2: FULL_BACKUP example  
    backup_response = test_full_backup_example()
    if backup_response:
        show_json_output_sample(backup_response, "FULL_BACKUP EXAMPLE")
    
    print(f"\n" + "=" * 80)
    print("🏁 TESTING COMPLETE")
    print("=" * 80)
    print("Key Structured Citation Fields Added:")
    print("  ├─ interview_id: Unique interview identifier")
    print("  ├─ executive_name: Name of the executive") 
    print("  ├─ chunk_id: Unique chunk identifier")
    print("  └─ similarity_score: Vector similarity score")
    print()
    print("Ready for EI intelligence layer validation! ✅")


if __name__ == "__main__":
    main()