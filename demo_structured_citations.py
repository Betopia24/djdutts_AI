#!/usr/bin/env python3
"""
Demo: Structured Citation Metadata for EI Intelligence Layer

This demonstrates the enhanced JSON response format with structured citation data.
Shows both PRIMARY and FULL_BACKUP examples as requested.
"""

import json
from datetime import datetime

def show_primary_example():
    """Show PRIMARY example with structured citation metadata."""
    print("=" * 80)
    print("🎯 PRIMARY EXAMPLE - High Authority Bounded Insight")
    print("=" * 80)
    print("Query: How do successful leaders approach building innovative teams?")
    
    # Mock PRIMARY response with enhanced structured citation metadata
    primary_response = {
        "status": "success",
        "snapshot_type": "interview_based",
        "output_class": "primary", 
        "question": "How do successful leaders approach building innovative teams and managing organizational change?",
        "answer": "Based on insights from successful executives, innovative team building requires a multi-faceted approach. Sangita Reddy from Apollo Hospitals emphasizes creating ecosystems of advanced technology and good leadership, stating 'My father quickly created an ecosystem of advanced technology, good leadership and the best medical professionals.' Philippe Morin from Clariane highlights the importance of diverse talent, explaining 'We are able to attract more talent thanks to the reputation and the size of our network. Having this good reputation allows us to prepare a career path.' Both leaders demonstrate that successful innovation comes from combining strategic vision with talent development and creating environments where teams can thrive through cross-functional collaboration.",
        "chunks_used": 3,
        "top_score": 0.847,
        "ei_competencies": ["leadership", "innovation", "social_skills"],
        "sources": [
            {
                # Legacy fields (maintained for backward compatibility)
                "type": "ceo_interview",
                "reference": "Sangita Reddy",
                "score": 0.847,
                
                # ✅ NEW: Structured Citation Metadata for EI
                "interview_id": "interview_sangita_reddy",
                "executive_name": "Sangita Reddy",
                "chunk_id": "chunk_1",
                "similarity_score": 0.847
            },
            {
                # Legacy fields 
                "type": "ceo_interview", 
                "reference": "Philippe Morin",
                "score": 0.782,
                
                # ✅ NEW: Structured Citation Metadata for EI
                "interview_id": "interview_philippe_morin",
                "executive_name": "Philippe Morin",
                "chunk_id": "chunk_2",
                "similarity_score": 0.782
            },
            {
                # Legacy fields
                "type": "ceo_interview",
                "reference": "Xavier Gondaud", 
                "score": 0.734,
                
                # ✅ NEW: Structured Citation Metadata for EI
                "interview_id": "interview_xavier_gondaud",
                "executive_name": "Xavier Gondaud",
                "chunk_id": "chunk_3",
                "similarity_score": 0.734
            }
        ],
        "confidence_level": "high",
        "retrieval_quality": "excellent",
        "gate_decision": {
            "output_class": "primary",
            "reason": "Met PRIMARY thresholds: 3 chunks (≥2), 3 unique interviews (≥2)",
            "chunks_passed_gate": 3,
            "unique_interviews": 3,
            "top_similarity": 0.847,
            "allow_generation": True,
            "is_deterministic": True
        },
        "flagged": False,
        "warning": None
    }
    
    print(f"\n📊 Response Details:")
    print(f"   ├─ Status: {primary_response['status']}")
    print(f"   ├─ Snapshot Type: {primary_response['snapshot_type']}")
    print(f"   ├─ Output Class: {primary_response['output_class']}")
    print(f"   ├─ Chunks Used: {primary_response['chunks_used']} (≥2 required ✅)")
    print(f"   ├─ Unique Interviews: {primary_response['gate_decision']['unique_interviews']} (≥2 required ✅)")
    print(f"   └─ Confidence Level: {primary_response['confidence_level']}")
    
    print(f"\n📖 Structured Citation Metadata:")
    for i, source in enumerate(primary_response['sources'], 1):
        print(f"   Citation {i}:")
        print(f"   ├─ Interview ID: {source['interview_id']}")
        print(f"   ├─ Executive Name: {source['executive_name']}")
        print(f"   ├─ Chunk ID: {source['chunk_id']}")
        print(f"   ├─ Similarity Score: {source['similarity_score']:.3f}")
        print(f"   └─ Source Type: {source['type']}")
    
    return primary_response

def show_full_backup_example():
    """Show FULL_BACKUP example with no relevant chunks."""
    print("\n" + "=" * 80)
    print("🛑 FULL_BACKUP EXAMPLE - No Relevant Chunks")
    print("=" * 80)
    print("Query: What is the atomic weight of plutonium in quantum mechanics?")
    
    # Mock FULL_BACKUP response - no relevant chunks, no authoritative language
    backup_response = {
        "status": "refused",
        "snapshot_type": "full_backup_refusal", 
        "output_class": "full_backup",
        "question": "What is the atomic weight of plutonium in quantum mechanics?",
        "answer": "We cannot provide a bounded insight for this question. The evidence that passed our quality gate is insufficient to generate an authoritative response grounded in the retrieved data.",
        "chunks_used": 0,
        "top_score": 0.127,
        "ei_competencies": ["general"],
        "sources": [],  # ✅ Empty - no relevant chunks found
        "confidence_level": "insufficient",
        "retrieval_quality": "below_threshold",
        "gate_decision": {
            "output_class": "full_backup",
            "reason": "FULL_BACKUP: 0 chunks passed gate (< 1 minimum threshold)",
            "chunks_passed_gate": 0,
            "unique_interviews": 0,
            "top_similarity": 0.127,
            "allow_generation": False,
            "is_deterministic": True
        },
        "flagged": True,
        "warning": "⚠️ Insufficient evidence - deterministic refusal/reframe",
        "recommendation": "Please rephrase your question or provide more context."
    }
    
    print(f"\n📊 Response Details:")
    print(f"   ├─ Status: {backup_response['status']}")
    print(f"   ├─ Snapshot Type: {backup_response['snapshot_type']}")
    print(f"   ├─ Output Class: {backup_response['output_class']}")
    print(f"   ├─ Chunks Used: {backup_response['chunks_used']} (0 chunks ✅)")
    print(f"   ├─ Sources: {len(backup_response['sources'])} (empty ✅)")
    print(f"   └─ Flagged: {backup_response['flagged']} ✅")
    
    print(f"\n📖 Citation Metadata:")
    print(f"   No citations (sources empty - expected for FULL_BACKUP)")
    
    print(f"\n📝 Answer (Non-Authoritative):")
    print(f"   \"{backup_response['answer']}\"")
    print(f"   ✅ No authoritative language - proper refusal")
    
    return backup_response

def show_json_samples():
    """Show clean JSON samples of both response types."""
    print("\n" + "=" * 80)
    print("🔍 JSON SAMPLES FOR EI VALIDATION")
    print("=" * 80)
    
    print("\n📝 PRIMARY Example JSON (Structured Citations):")
    print("-" * 50)
    primary_sample = {
        "status": "success",
        "snapshot_type": "interview_based", 
        "output_class": "primary",
        "chunks_used": 3,
        "sources": [
            {
                "interview_id": "interview_sangita_reddy",
                "executive_name": "Sangita Reddy",
                "chunk_id": "chunk_1",
                "similarity_score": 0.847,
                "type": "ceo_interview"
            },
            {
                "interview_id": "interview_philippe_morin", 
                "executive_name": "Philippe Morin",
                "chunk_id": "chunk_2",
                "similarity_score": 0.782,
                "type": "ceo_interview"
            }
        ],
        "gate_decision": {
            "output_class": "primary",
            "unique_interviews": 3,
            "chunks_passed_gate": 3
        }
    }
    print(json.dumps(primary_sample, indent=2))
    
    print("\n📝 FULL_BACKUP Example JSON (No Citations):")
    print("-" * 50)
    backup_sample = {
        "status": "refused",
        "snapshot_type": "full_backup_refusal",
        "output_class": "full_backup", 
        "chunks_used": 0,
        "sources": [],  # Empty sources array
        "flagged": True,
        "gate_decision": {
            "output_class": "full_backup",
            "chunks_passed_gate": 0,
            "allow_generation": False
        }
    }
    print(json.dumps(backup_sample, indent=2))

def main():
    """Main demo runner."""
    print("🧪 STRUCTURED CITATION METADATA DEMO")
    print("Enhanced JSON responses for EI intelligence layer validation")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Show both examples
    primary_response = show_primary_example()
    backup_response = show_full_backup_example()
    
    # Show JSON samples
    show_json_samples()
    
    print(f"\n" + "=" * 80)
    print("✅ STRUCTURED CITATION METADATA READY")
    print("=" * 80)
    print("New fields added to each source:")
    print("  ├─ interview_id: Unique interview identifier")
    print("  ├─ executive_name: Name of the executive")
    print("  ├─ chunk_id: Unique chunk identifier") 
    print("  └─ similarity_score: Vector similarity score")
    print()
    print("Example scenarios covered:")
    print("  ├─ PRIMARY: ≥2 interviews, ≥2 chunks, structured citations")
    print("  └─ FULL_BACKUP: 0 chunks, empty sources, non-authoritative")
    print()
    print("Ready for EI intelligence layer validation! 🚀")

if __name__ == "__main__":
    main()