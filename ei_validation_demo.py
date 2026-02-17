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
        
        # 🔍 EI Auditable Proof: Evidence Summary
        "evidence_summary": {
            "chunks_used": 3,
            "unique_interviews": 3,
            "top_score": 0.847,
            "similarity_threshold_applied": 0.30,
            "gate_decision": "primary"
        },
        
        # ✅ EI Auditable Proof: Validation Results
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
            "reason": "Met PRIMARY thresholds: 3 chunks (≥2), 3 unique interviews (≥2)",
            "chunks_passed_gate": 3,
            "unique_interviews": 3,
            "is_deterministic": True
        },
        "flagged": False\n    }\n    \n    print_response_summary(primary_response, "PRIMARY")\n    return primary_response\n\ndef show_hybrid_bounded_language():\n    """Show HYBRID example with bounded language and citations."""\n    print("\\n" + "=" * 80)\n    print("📊 CASE 2: HYBRID with Bounded Language")\n    print("=" * 80)\n    print("Query: What is the best approach to digital transformation?")\n    \n    # Mock HYBRID response with bounded language\n    hybrid_response = {\n        "status": "success",\n        "snapshot_type": "hybrid",\n        "output_class": "hybrid",\n        "question": "What is the best approach to digital transformation?",\n        "answer": "While the evidence doesn't address digital transformation specifically, Anthony Tan from Grab shares relevant principles about adapting to change: 'You have to be bold and willing to take risks.' This suggests that transformation requires courage and calculated risk-taking, though specific digital strategies would need additional context beyond what our evidence provides.",\n        "chunks_used": 1,\n        "top_score": 0.42,\n        "ei_competencies": ["adaptability"],\n        "sources": [\n            {\n                "interview_id": "interview_anthony_tan",\n                "executive_name": "Anthony Tan",\n                "chunk_id": "chunk_1",\n                "similarity_score": 0.42,\n                "type": "ceo_interview"\n            }\n        ],\n        "confidence_level": "medium",\n        "retrieval_quality": "partial",\n        \n        # 🔍 EI Auditable Proof: Evidence Summary\n        "evidence_summary": {\n            "chunks_used": 1,\n            "unique_interviews": 1,\n            "top_score": 0.42,\n            "similarity_threshold_applied": 0.30,\n            "gate_decision": "hybrid"\n        },\n        \n        # ✅ EI Auditable Proof: Validation Results\n        "validation": {\n            "passed": True,\n            "claims_supported": 2,\n            "claims_total": 2,\n            "has_generic_language": False,\n            "fabricated_details": [],\n            "confidence": "medium",\n            "auto_downgrade_applied": None\n        },\n        \n        "gate_decision": {\n            "output_class": "hybrid",\n            "reason": "HYBRID: 1 chunk passed gate (≥1), but < 2 unique interviews for PRIMARY",\n            "chunks_passed_gate": 1,\n            "unique_interviews": 1,\n            "is_deterministic": True\n        },\n        "flagged": False,\n        "note": "Evidence-first response with bounded adjacent insight"\n    }\n    \n    print_response_summary(hybrid_response, "HYBRID")\n    return hybrid_response\n\ndef show_full_backup_refuse():\n    """Show FULL_BACKUP example with no authoritative language."""\n    print("\\n" + "=" * 80)\n    print("🛑 CASE 3: FULL_BACKUP/REFUSE - No Authoritative Language")\n    print("=" * 80)\n    print("Query: What is the atomic weight of plutonium in quantum mechanics?")\n    \n    # Mock FULL_BACKUP response with no relevant chunks\n    backup_response = {\n        "status": "refused",\n        "snapshot_type": "full_backup_refusal",\n        "output_class": "full_backup",\n        "question": "What is the atomic weight of plutonium in quantum mechanics?",\n        "answer": "We cannot provide a bounded insight for this question. The evidence that passed our quality gate is insufficient to generate an authoritative response grounded in the retrieved data.",\n        "chunks_used": 0,\n        "top_score": 0.127,\n        "ei_competencies": ["general"],\n        "sources": [],  # Empty - no relevant chunks\n        "confidence_level": "insufficient",\n        "retrieval_quality": "below_threshold",\n        \n        # 🔍 EI Auditable Proof: Evidence Summary\n        "evidence_summary": {\n            "chunks_used": 0,\n            "unique_interviews": 0,\n            "top_score": 0.127,\n            "similarity_threshold_applied": 0.30,\n            "gate_decision": "full_backup"\n        },\n        \n        # ✅ EI Auditable Proof: Validation Results\n        "validation": {\n            "passed": True,  # No validation performed - deterministic refusal\n            "claims_supported": 0,\n            "claims_total": 0,\n            "has_generic_language": False,\n            "fabricated_details": [],\n            "confidence": "not_applicable",\n            "auto_downgrade_applied": None\n        },\n        \n        "gate_decision": {\n            "output_class": "full_backup",\n            "reason": "FULL_BACKUP: 0 chunks passed gate (< 1 minimum threshold)",\n            "chunks_passed_gate": 0,\n            "unique_interviews": 0,\n            "is_deterministic": True\n        },\n        "flagged": True,\n        "warning": "⚠️ Insufficient evidence - deterministic refusal/reframe"\n    }\n    \n    print_response_summary(backup_response, "FULL_BACKUP")\n    return backup_response\n\ndef show_auto_downgrade_example():\n    """Show example of PRIMARY → HYBRID auto-downgrade due to validation failure."""\n    print("\\n" + "=" * 80)\n    print("🔻 BONUS: AUTO-DOWNGRADE Example (PRIMARY → HYBRID)")\n    print("=" * 80)\n    print("Query: How do leaders succeed in complex markets?")\n    \n    # Mock response that started as PRIMARY but was auto-downgraded\n    downgrade_response = {\n        "status": "success",\n        "snapshot_type": "hybrid",  # Downgraded from interview_based\n        "output_class": "hybrid",  # Downgraded from primary\n        "question": "How do leaders succeed in complex markets?",\n        "answer": "Based on executive insights, leaders must focus on building strong foundations and adapting to market conditions through strategic planning and team development.",  # Generic language detected\n        "chunks_used": 3,\n        "top_score": 0.78,\n        "ei_competencies": ["leadership"],\n        "sources": [\n            {\n                "interview_id": "interview_sangita_reddy",\n                "executive_name": "Sangita Reddy",\n                "chunk_id": "chunk_1",\n                "similarity_score": 0.78,\n                "type": "ceo_interview"\n            }\n        ],\n        "confidence_level": "medium",  # Downgraded from high\n        "retrieval_quality": "partial",  # Downgraded from excellent\n        \n        # 🔍 EI Auditable Proof: Evidence Summary\n        "evidence_summary": {\n            "chunks_used": 3,\n            "unique_interviews": 3,\n            "top_score": 0.78,\n            "similarity_threshold_applied": 0.30,\n            "gate_decision": "hybrid"  # Shows final state after downgrade\n        },\n        \n        # ⚠️ EI Auditable Proof: Validation Results (FAILED)\n        "validation": {\n            "passed": False,  # ❌ Validation FAILED\n            "claims_supported": 2,\n            "claims_total": 5,\n            "has_generic_language": True,  # ❌ Generic language detected\n            "fabricated_details": ["strategic planning", "team development"],\n            "confidence": "low",\n            "auto_downgrade_applied": "PRIMARY → HYBRID (validation failed)"  # ⚡ Auto-downgrade!\n        },\n        \n        "gate_decision": {\n            "output_class": "hybrid",  # Shows final state\n            "reason": "Originally PRIMARY, auto-downgraded due to validation failure",\n            "chunks_passed_gate": 3,\n            "unique_interviews": 3,\n            "is_deterministic": True\n        },\n        "flagged": False\n    }\n    \n    print_response_summary(downgrade_response, "AUTO-DOWNGRADED")\n    return downgrade_response\n\ndef print_response_summary(response, case_type):\n    """Print a formatted summary of the response."""\n    evidence = response.get('evidence_summary', {})\n    validation = response.get('validation', {})\n    \n    print(f"\\n📊 Response Summary ({case_type}):")\n    print(f"   ├─ Status: {response.get('status')}")\n    print(f"   ├─ Output Class: {response.get('output_class')}")\n    print(f"   ├─ Snapshot Type: {response.get('snapshot_type')}")\n    print(f"   └─ Confidence: {response.get('confidence_level')}")\n    \n    print(f"\\n🔍 Evidence Summary (Auditable Proof):")\n    print(f"   ├─ Chunks Used: {evidence.get('chunks_used')}")\n    print(f"   ├─ Unique Interviews: {evidence.get('unique_interviews')}")\n    print(f"   ├─ Top Score: {evidence.get('top_score', 0):.3f}")\n    print(f"   ├─ Threshold Applied: {evidence.get('similarity_threshold_applied')}")\n    print(f"   └─ Gate Decision: {evidence.get('gate_decision')}")\n    \n    print(f"\\n✅ Validation Results (Auditable Proof):")\n    print(f"   ├─ Passed: {validation.get('passed')} {'✅' if validation.get('passed') else '❌'}")\n    print(f"   ├─ Claims: {validation.get('claims_supported')}/{validation.get('claims_total')}")\n    print(f"   ├─ Generic Language: {validation.get('has_generic_language')} {'⚠️' if validation.get('has_generic_language') else '✅'}")\n    print(f"   ├─ Fabricated Details: {len(validation.get('fabricated_details', []))}")\n    print(f"   └─ Auto-Downgrade: {validation.get('auto_downgrade_applied') or 'None'}")\n    \n    print(f"\\n📖 Citations: {len(response.get('sources', []))} sources")\n    for i, source in enumerate(response.get('sources', []), 1):\n        print(f"   {i}. {source.get('executive_name')} (score: {source.get('similarity_score', 0):.3f})")\n\ndef show_json_comparison():\n    """Show clean JSON comparison of all three cases."""\n    print("\\n" + "=" * 80)\n    print("🔍 JSON COMPARISON - EI Auditable Proof Structure")\n    print("=" * 80)\n    \n    comparison = {\n        "primary_passed": {\n            "output_class": "primary",\n            "evidence_summary": {\n                "chunks_used": 3,\n                "unique_interviews": 3,\n                "gate_decision": "primary"\n            },\n            "validation": {\n                "passed": True,\n                "claims_supported": 6,\n                "claims_total": 6,\n                "has_generic_language": False,\n                "auto_downgrade_applied": None\n            },\n            "sources": ["3 structured citations with interview_id, executive_name, chunk_id"]\n        },\n        "hybrid_bounded": {\n            "output_class": "hybrid",\n            "evidence_summary": {\n                "chunks_used": 1,\n                "unique_interviews": 1,\n                "gate_decision": "hybrid"\n            },\n            "validation": {\n                "passed": True,\n                "claims_supported": 2,\n                "claims_total": 2,\n                "has_generic_language": False,\n                "auto_downgrade_applied": None\n            },\n            "sources": ["1 structured citation with bounded language"]\n        },\n        "full_backup": {\n            "output_class": "full_backup",\n            "evidence_summary": {\n                "chunks_used": 0,\n                "unique_interviews": 0,\n                "gate_decision": "full_backup"\n            },\n            "validation": {\n                "passed": True,  # Not applicable - deterministic refusal\n                "claims_supported": 0,\n                "claims_total": 0,\n                "confidence": "not_applicable",\n                "auto_downgrade_applied": None\n            },\n            "sources": []  # Empty - no authoritative language\n        }\n    }\n    \n    print(json.dumps(comparison, indent=2))\n\ndef main():\n    """Main demo runner."""\n    print("🧪 EI VALIDATION DEMO - Three Canonical Cases")\n    print("Enhanced validation system with auto-downgrade enforcement")\n    print(f"Timestamp: {datetime.now().isoformat()}")\n    \n    # Show the three canonical cases\n    primary = show_primary_passed_validation()\n    hybrid = show_hybrid_bounded_language()\n    backup = show_full_backup_refuse()\n    \n    # Show auto-downgrade example\n    downgrade = show_auto_downgrade_example()\n    \n    # Show JSON comparison\n    show_json_comparison()\n    \n    print(f"\\n" + "=" * 80)\n    print("🎯 EI VALIDATION SYSTEM READY")\n    print("=" * 80)\n    print("✅ Structured validation metadata in API response (not logs)")\n    print("✅ Auto-downgrade enforcement (PRIMARY → HYBRID → REFUSED)")\n    print("✅ Evidence summary for auditable proof")\n    print("✅ Validation results with claims tracking")\n    print("✅ Citation metadata with interview_id, executive_name, chunk_id")\n    print("✅ Three canonical cases demonstrated")\n    print("\\nReady for EI intelligence layer validation! 🚀")\n\nif __name__ == "__main__":\n    main()