#!/usr/bin/env python3
"""
EI Validation Demo: Three Canonical Cases

Demonstrates the enhanced EI validation system with auto-downgrade enforcement:
1. PRIMARY with validation passed=true
2. HYBRID with bounded language and citations  
3. FULL_BACKUP/REFUSE with no authoritative language

Shows structured validation metadata in API response for auditable proof.
"""

import json
from datetime import datetime


def enrich_example_response(response, query, llm_called, llm_blocked, llm_block_reason=None, downgrade_applied=None):
    """Normalize example payloads so each case exposes the requested audit fields."""
    sources = response.get("sources", [])
    similarity_scores = [source.get("similarity_score", 0.0) for source in sources]
    unique_interviews = response.get(
        "unique_interviews",
        response.get("evidence_summary", {}).get("unique_interviews", len({source.get("executive_name", "Unknown") for source in sources}))
    )
    response.setdefault("question", query)
    response.setdefault("retrieval_count", response.get("chunks_used", 0))
    response.setdefault("unique_interviews", unique_interviews)
    response.setdefault("similarity_scores", similarity_scores)
    response.setdefault("llm_called", llm_called)
    response.setdefault("llm_blocked", llm_blocked)
    response.setdefault("llm_block_reason", llm_block_reason)
    response.setdefault("validation_result", response.get("validation"))
    response.setdefault("downgrade_applied", downgrade_applied)
    return response

def show_primary_passed_validation():
    """Show PRIMARY example with validation passed=true."""
    print("=" * 80)
    print("✅ CASE 1: PRIMARY with Validation PASSED")
    print("=" * 80)
    print("Query: How do successful leaders approach building innovative teams?")
    
    # Mock PRIMARY response where validation PASSES
    primary_response = {
        "status": "success",
        "snapshot_type": "interview_based",
        "output_class": "primary",
        "question": "How do successful leaders approach building innovative teams?",
        "answer": "Based on insights from successful executives, Sangita Reddy from Apollo Hospitals emphasizes creating ecosystems of advanced technology and good leadership, stating 'My father quickly created an ecosystem of advanced technology, good leadership and the best medical professionals.' Philippe Morin from Clariane highlights the importance of diverse talent, explaining 'We are able to attract more talent thanks to the reputation and the size of our network.' These leaders demonstrate focused strategies for building innovative teams through systematic approaches.",
        "chunks_used": 3,
        "top_score": 0.847,
        "ei_competencies": ["leadership", "innovation", "social_skills"],
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
            },
            {
                "interview_id": "interview_xavier_gondaud",
                "executive_name": "Xavier Gondaud",
                "chunk_id": "chunk_3",
                "similarity_score": 0.734,
                "type": "ceo_interview"
            }
        ],
        "confidence_level": "high",
        "retrieval_quality": "excellent",
        
        # EI Auditable Proof: Evidence Summary
        "evidence_summary": {
            "chunks_used": 3,
            "unique_interviews": 3,
            "top_score": 0.847,
            "similarity_threshold_applied": 0.30,
            "gate_decision": "primary"
        },
        
        # EI Auditable Proof: Validation Results
        "validation": {
            "passed": True,
            "claims_supported": 6,
            "claims_total": 6,
            "has_generic_language": False,
            "fabricated_details": [],
            "confidence": "high",
            "auto_downgrade_applied": None
        },
        
        "gate_decision": {
            "output_class": "primary",
            "reason": "Met PRIMARY thresholds: 3 chunks (>=2), 3 unique interviews (>=2)",
            "chunks_passed_gate": 3,
            "unique_interviews": 3,
            "is_deterministic": True
        },
        "flagged": False
    }
    
    print_response_summary(
        enrich_example_response(
            primary_response,
            primary_response["question"],
            llm_called=True,
            llm_blocked=False,
        ),
        "PRIMARY"
    )
    return primary_response

def show_hybrid_bounded_language():
    """Show HYBRID example with bounded language and citations."""
    print("\n" + "=" * 80)
    print("📊 CASE 2: HYBRID with Bounded Language")
    print("=" * 80)
    print("Query: What is the best approach to digital transformation?")
    
    # Mock HYBRID response with bounded language
    hybrid_response = {
        "status": "success",
        "snapshot_type": "hybrid",
        "output_class": "hybrid",
        "question": "What is the best approach to digital transformation?",
        "answer": "While the evidence doesn't address digital transformation specifically, Anthony Tan from Grab shares relevant principles about adapting to change: 'You have to be bold and willing to take risks.' This suggests that transformation requires courage and calculated risk-taking, though specific digital strategies would need additional context beyond what our evidence provides.",
        "chunks_used": 1,
        "top_score": 0.42,
        "ei_competencies": ["adaptability"],
        "sources": [
            {
                "interview_id": "interview_anthony_tan",
                "executive_name": "Anthony Tan",
                "chunk_id": "chunk_1",
                "similarity_score": 0.42,
                "type": "ceo_interview"
            }
        ],
        "confidence_level": "medium",
        "retrieval_quality": "partial",
        
        # EI Auditable Proof: Evidence Summary
        "evidence_summary": {
            "chunks_used": 1,
            "unique_interviews": 1,
            "top_score": 0.42,
            "similarity_threshold_applied": 0.30,
            "gate_decision": "hybrid"
        },
        
        # EI Auditable Proof: Validation Results
        "validation": {
            "passed": True,
            "claims_supported": 2,
            "claims_total": 2,
            "has_generic_language": False,
            "fabricated_details": [],
            "confidence": "medium",
            "auto_downgrade_applied": None
        },
        
        "gate_decision": {
            "output_class": "hybrid",
            "reason": "HYBRID: 1 chunk passed gate (>=1), but < 2 unique interviews for PRIMARY",
            "chunks_passed_gate": 1,
            "unique_interviews": 1,
            "is_deterministic": True
        },
        "flagged": False,
        "note": "Evidence-first response with bounded adjacent insight"
    }
    
    print_response_summary(
        enrich_example_response(
            hybrid_response,
            hybrid_response["question"],
            llm_called=True,
            llm_blocked=False,
        ),
        "HYBRID"
    )
    return hybrid_response

def show_full_backup_refuse():
    """Show FULL_BACKUP example with no authoritative language."""
    print("\n" + "=" * 80)
    print("🛑 CASE 3: FULL_BACKUP/REFUSE - No Authoritative Language")
    print("=" * 80)
    print("Query: What is the atomic weight of plutonium in quantum mechanics?")
    
    # Mock FULL_BACKUP response with no relevant chunks
    backup_response = {
        "status": "refused",
        "snapshot_type": "full_backup_refusal",
        "output_class": "full_backup",
        "question": "What is the atomic weight of plutonium in quantum mechanics?",
        "answer": "We cannot provide a bounded insight for this question. The evidence that passed our quality gate is insufficient to generate an authoritative response grounded in the retrieved data.",
        "chunks_used": 0,
        "top_score": 0.127,
        "ei_competencies": ["general"],
        "sources": [],  # Empty - no relevant chunks
        "confidence_level": "insufficient",
        "retrieval_quality": "below_threshold",
        
        # EI Auditable Proof: Evidence Summary
        "evidence_summary": {
            "chunks_used": 0,
            "unique_interviews": 0,
            "top_score": 0.127,
            "similarity_threshold_applied": 0.30,
            "gate_decision": "full_backup"
        },
        
        # EI Auditable Proof: Validation Results
        "validation": {
            "passed": True,  # No validation performed - deterministic refusal
            "claims_supported": 0,
            "claims_total": 0,
            "has_generic_language": False,
            "fabricated_details": [],
            "confidence": "not_applicable",
            "auto_downgrade_applied": None
        },
        
        "gate_decision": {
            "output_class": "full_backup",
            "reason": "FULL_BACKUP: 0 chunks passed gate (< 1 minimum threshold)",
            "chunks_passed_gate": 0,
            "unique_interviews": 0,
            "is_deterministic": True
        },
        "flagged": True,
        "warning": "⚠️ Insufficient evidence - deterministic refusal/reframe"
    }
    
    print_response_summary(
        enrich_example_response(
            backup_response,
            backup_response["question"],
            llm_called=False,
            llm_blocked=True,
            llm_block_reason="Deterministic gate blocked generation before any LLM call",
        ),
        "FULL_BACKUP"
    )
    return backup_response

def show_auto_downgrade_example():
    """Show example of PRIMARY → HYBRID auto-downgrade due to validation failure."""
    print("\n" + "=" * 80)
    print("🔻 BONUS: AUTO-DOWNGRADE Example (PRIMARY → HYBRID)")
    print("=" * 80)
    print("Query: How do leaders succeed in complex markets?")
    print("Original: PRIMARY → Validation FAILED → Auto-downgraded to HYBRID")
    
    # Mock response that started as PRIMARY but was auto-downgraded
    downgrade_response = {
        "status": "success",
        "snapshot_type": "hybrid",  # Downgraded from interview_based
        "output_class": "hybrid",  # Downgraded from primary
        "question": "How do leaders succeed in complex markets?",
        "answer": "Based on executive insights, leaders must focus on building strong foundations and adapting to market conditions through strategic planning and team development.",  # Generic language detected
        "chunks_used": 3,
        "top_score": 0.78,
        "ei_competencies": ["leadership"],
        "sources": [
            {
                "interview_id": "interview_sangita_reddy",
                "executive_name": "Sangita Reddy",
                "chunk_id": "chunk_1",
                "similarity_score": 0.78,
                "type": "ceo_interview"
            }
        ],
        "confidence_level": "medium",  # Downgraded from high
        "retrieval_quality": "partial",  # Downgraded from excellent
        
        # EI Auditable Proof: Evidence Summary
        "evidence_summary": {
            "chunks_used": 3,
            "unique_interviews": 3,
            "top_score": 0.78,
            "similarity_threshold_applied": 0.30,
            "gate_decision": "hybrid"  # Shows final state after downgrade
        },
        
        # EI Auditable Proof: Validation Results (FAILED)
        "validation": {
            "passed": False,  # Validation FAILED
            "claims_supported": 2,
            "claims_total": 5,
            "has_generic_language": True,  # Generic language detected
            "fabricated_details": ["strategic planning", "team development"],
            "confidence": "low",
            "auto_downgrade_applied": "PRIMARY → HYBRID (validation failed)"  # Auto-downgrade!
        },
        
        "gate_decision": {
            "output_class": "hybrid",  # Shows final state
            "reason": "Originally PRIMARY, auto-downgraded due to validation failure",
            "chunks_passed_gate": 3,
            "unique_interviews": 3,
            "is_deterministic": True
        },
        "flagged": False
    }
    
    print_response_summary(
        enrich_example_response(
            downgrade_response,
            downgrade_response["question"],
            llm_called=True,
            llm_blocked=False,
            downgrade_applied="PRIMARY → HYBRID (validation failed)",
        ),
        "AUTO-DOWNGRADED"
    )
    return downgrade_response

def print_response_summary(response, case_type):
    """Print a formatted summary of the response."""
    query = response.get('question', 'N/A')
    evidence = response.get('evidence_summary', {})
    validation = response.get('validation', {})
    sources = response.get('sources', [])
    final_response = response.get('answer', '')
    
    print(f"\n📊 Response Summary ({case_type}):")
    print(f"   ├─ Query: {query}")
    print(f"   ├─ Status: {response.get('status')}")
    print(f"   ├─ Output Class: {response.get('output_class')}")
    print(f"   ├─ Snapshot Type: {response.get('snapshot_type')}")
    print(f"   └─ Confidence: {response.get('confidence_level')}")

    print(f"\n🤖 LLM Audit:")
    print(f"   ├─ LLM Called: {response.get('llm_called')}")
    print(f"   ├─ LLM Blocked: {response.get('llm_blocked')}")
    print(f"   └─ Block Reason: {response.get('llm_block_reason') or 'None'}")
    
    print(f"\n🔍 Evidence Summary (Auditable Proof):")
    print(f"   ├─ Chunks Used: {evidence.get('chunks_used')}")
    print(f"   ├─ Unique Interviews: {evidence.get('unique_interviews')}")
    print(f"   ├─ Top Score: {evidence.get('top_score', 0):.3f}")
    print(f"   ├─ Threshold Applied: {evidence.get('similarity_threshold_applied')}")
    print(f"   └─ Gate Decision: {evidence.get('gate_decision')}")

    print(f"\n📈 Retrieval Audit:")
    print(f"   ├─ Retrieval Count: {response.get('retrieval_count')}")
    print(f"   ├─ Unique Interview Count: {response.get('unique_interviews')}")
    print(f"   └─ Similarity Scores: {response.get('similarity_scores')}")
    
    print(f"\n✅ Validation Results (Auditable Proof):")
    validation_icon = '✅' if validation.get('passed') else '❌'
    generic_icon = '⚠️' if validation.get('has_generic_language') else '✅'
    print(f"   ├─ Passed: {validation.get('passed')} {validation_icon}")
    print(f"   ├─ Claims: {validation.get('claims_supported')}/{validation.get('claims_total')}")
    print(f"   ├─ Generic Language: {validation.get('has_generic_language')} {generic_icon}")
    print(f"   ├─ Fabricated Details: {len(validation.get('fabricated_details', []))}")
    downgrade_text = validation.get('auto_downgrade_applied') or 'None'
    downgrade_icon = '🔻' if validation.get('auto_downgrade_applied') else '✅'
    print(f"   └─ Auto-Downgrade: {downgrade_text} {downgrade_icon}")
    
    print(f"\n📖 Source References: {len(sources)} sources")
    for i, source in enumerate(sources, 1):
        print(
            f"   {i}. {source.get('executive_name')} | "
            f"{source.get('interview_id')} | {source.get('chunk_id')} | "
            f"score={source.get('similarity_score', 0):.3f}"
        )

    print(f"\n📝 Final Response Returned:")
    print(f"   {final_response}")

def show_json_comparison():
    """Show clean JSON comparison of all three cases."""
    print("\n" + "=" * 80)
    print("🔍 JSON COMPARISON - EI Auditable Proof Structure")
    print("=" * 80)
    
    comparison = {
        "primary_passed": {
            "output_class": "primary",
            "evidence_summary": {
                "chunks_used": 3,
                "unique_interviews": 3,
                "gate_decision": "primary"
            },
            "validation": {
                "passed": True,
                "claims_supported": 6,
                "claims_total": 6,
                "has_generic_language": False,
                "auto_downgrade_applied": None
            },
            "sources": ["3 structured citations with interview_id, executive_name, chunk_id"]
        },
        "hybrid_bounded": {
            "output_class": "hybrid",
            "evidence_summary": {
                "chunks_used": 1,
                "unique_interviews": 1,
                "gate_decision": "hybrid"
            },
            "validation": {
                "passed": True,
                "claims_supported": 2,
                "claims_total": 2,
                "has_generic_language": False,
                "auto_downgrade_applied": None
            },
            "sources": ["1 structured citation with bounded language"]
        },
        "full_backup": {
            "output_class": "full_backup",
            "evidence_summary": {
                "chunks_used": 0,
                "unique_interviews": 0,
                "gate_decision": "full_backup"
            },
            "validation": {
                "passed": True,  # Not applicable - deterministic refusal
                "claims_supported": 0,
                "claims_total": 0,
                "confidence": "not_applicable",
                "auto_downgrade_applied": None
            },
            "sources": []  # Empty - no authoritative language
        }
    }
    
    print(json.dumps(comparison, indent=2))

def main():
    """Main demo runner."""
    print("🧪 EI VALIDATION DEMO - Three Canonical Cases")
    print("Enhanced validation system with auto-downgrade enforcement")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Show the three canonical cases
    primary = show_primary_passed_validation()
    hybrid = show_hybrid_bounded_language()
    backup = show_full_backup_refuse()
    
    # Show auto-downgrade example
    downgrade = show_auto_downgrade_example()
    
    # Show JSON comparison
    show_json_comparison()
    
    print(f"\n" + "=" * 80)
    print("🎯 EI VALIDATION SYSTEM READY")
    print("=" * 80)
    print("✅ Structured validation metadata in API response (not logs)")
    print("✅ Auto-downgrade enforcement (PRIMARY → HYBRID → REFUSED)")
    print("✅ Evidence summary for auditable proof")
    print("✅ Validation results with claims tracking")
    print("✅ Citation metadata with interview_id, executive_name, chunk_id")
    print("✅ Three canonical cases demonstrated")
    print("\nReady for EI intelligence layer validation! 🚀")

if __name__ == "__main__":
    main()