#!/usr/bin/env python3
"""
========================================================================================
DEMO: Evidence Intelligence (EI) System - Three Cases End-to-End
========================================================================================

This script demonstrates the complete EI pipeline with three distinct scenarios:

CASE 1: Strong Evidence → PRIMARY Snapshot
    - Question matches multiple interview sources
    - Deterministic gate: PRIMARY
    - Output: Interview-based insight with citations

CASE 2: Partial Evidence → HYBRID Snapshot  
    - Question has limited matching content
    - Deterministic gate: HYBRID
    - Output: Bounded adjacent insight with clear limitations

CASE 3: No Evidence → FULL_BACKUP/REFUSE Response
    - Question has no relevant matches
    - Deterministic gate: REFUSED/FULL_BACKUP
    - Output: Deterministic refusal (no LLM strategy generation)

========================================================================================
ARCHITECTURE FLOW:
    Interview Ingestion → Chunking → Metadata → Embedding → FAISS Storage
    ↓
    Retrieval (Vector Search + Similarity Filtering)
    ↓
    DETERMINISTIC GATING (PRIMARY/HYBRID/FULL_BACKUP/REFUSED)
    ↓
    Evidence Pack Construction + Citation Tracking
    ↓
    Conditional LLM Generation (OR Deterministic Refusal)
    ↓
    Post-Generation Validation (Claim ↔ Evidence Alignment)
========================================================================================
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import the service
from app.services.interview.services import interviewServicees, OutputClass

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")


def print_section(text: str):
    print(f"\n{Colors.CYAN}{'─'*60}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'─'*60}{Colors.ENDC}")


def print_gate_decision(gate_decision: Dict[str, Any]):
    output_class = gate_decision.get('output_class', 'unknown').upper()
    
    color = Colors.GREEN if output_class == 'PRIMARY' else (
        Colors.WARNING if output_class == 'HYBRID' else Colors.FAIL
    )
    
    print(f"\n{color}🚪 GATE DECISION: {output_class}{Colors.ENDC}")
    print(f"   Reason: {gate_decision.get('reason', 'N/A')}")
    print(f"   Chunks Passed: {gate_decision.get('chunks_passed_gate', 0)}")
    print(f"   Unique Interviews: {gate_decision.get('unique_interviews', 0)}")
    print(f"   Top Similarity: {gate_decision.get('top_similarity', 0):.3f}")
    print(f"   Is Deterministic: {gate_decision.get('is_deterministic', True)}")


def print_citations(sources: list):
    if not sources:
        print(f"   {Colors.WARNING}No citations (insufficient evidence){Colors.ENDC}")
        return
    
    print(f"\n{Colors.BLUE}📚 CITATIONS:{Colors.ENDC}")
    for i, source in enumerate(sources, 1):
        print(f"   [{i}] {source.get('reference', 'Unknown')} ({source.get('type', 'unknown')}) - Score: {source.get('score', 0):.3f}")


def print_validation(validation: Dict[str, Any]):
    if not validation:
        return
    
    passed = validation.get('validation_passed', None)
    color = Colors.GREEN if passed else (Colors.FAIL if passed is False else Colors.WARNING)
    
    print(f"\n{color}🔍 POST-GENERATION VALIDATION:{Colors.ENDC}")
    print(f"   Validation Passed: {passed}")
    print(f"   Claims Verified: {validation.get('claims_verified', 'N/A')}/{validation.get('claims_total', 'N/A')}")
    print(f"   Generic Strategy Language: {validation.get('has_generic_strategy_language', 'N/A')}")
    print(f"   Confidence: {validation.get('confidence', 'N/A')}")
    
    if validation.get('issues'):
        print(f"   {Colors.FAIL}Issues: {', '.join(validation.get('issues', []))}{Colors.ENDC}")
    if validation.get('generic_phrases_found'):
        print(f"   {Colors.WARNING}Generic Phrases: {validation.get('generic_phrases_found')}{Colors.ENDC}")


def run_demo_case(service: interviewServicees, case_num: int, question: str, expected_outcome: str):
    """Run a single demo case and display results."""
    
    print_header(f"CASE {case_num}: {expected_outcome}")
    
    print(f"{Colors.BOLD}Question:{Colors.ENDC} {question}")
    print(f"\n{Colors.BLUE}Expected Outcome: {expected_outcome}{Colors.ENDC}")
    
    # Start timing
    start_time = time.time()
    
    # Execute the interview round with LLM scoring enabled for visibility
    result = service.interview_round(question, enable_llm_scoring=True)
    
    elapsed = time.time() - start_time
    
    # Display Gate Decision
    print_section("GATE DECISION (Deterministic)")
    if 'gate_decision' in result:
        print_gate_decision(result['gate_decision'])
    else:
        print(f"   {Colors.FAIL}Gate decision not available{Colors.ENDC}")
    
    # Display Snapshot Type & Output Class
    print_section("SNAPSHOT RESULT")
    snapshot_type = result.get('snapshot_type', 'unknown')
    output_class = result.get('output_class', result.get('gate_decision', {}).get('output_class', 'unknown'))
    
    type_color = Colors.GREEN if 'interview' in snapshot_type.lower() else (
        Colors.WARNING if 'hybrid' in snapshot_type.lower() else Colors.FAIL
    )
    
    print(f"   Snapshot Type: {type_color}{snapshot_type}{Colors.ENDC}")
    print(f"   Output Class: {type_color}{output_class.upper()}{Colors.ENDC}")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Confidence: {result.get('confidence_level', 'N/A')}")
    print(f"   Retrieval Quality: {result.get('retrieval_quality', 'N/A')}")
    print(f"   Chunks Used: {result.get('chunks_used', 0)}")
    print(f"   Top Score: {result.get('top_score', 0):.3f}")
    
    # Display Flagged status
    if result.get('flagged'):
        print(f"\n   {Colors.FAIL}⚠️ FLAGGED: {result.get('warning', 'Insufficient evidence')}{Colors.ENDC}")
    
    # Display Citations
    print_citations(result.get('sources', []))
    
    # Display Answer (truncated for readability)
    print_section("GENERATED RESPONSE")
    answer = result.get('answer', 'No answer generated')
    # Show first 600 chars with ellipsis if truncated
    if len(answer) > 600:
        print(f"{answer[:600]}...")
        print(f"\n{Colors.CYAN}[Response truncated - {len(answer)} total characters]{Colors.ENDC}")
    else:
        print(answer)
    
    # Display Post-Generation Validation
    if 'post_generation_validation' in result:
        print_section("POST-GENERATION VALIDATION")
        print_validation(result['post_generation_validation'])
    
    # Display LLM Evidence Scoring if available
    if 'llm_evidence_scoring' in result:
        scoring = result['llm_evidence_scoring']
        if 'scores' in scoring:
            print_section("LLM EVIDENCE SCORING (Post-Gate)")
            scores = scoring['scores']
            print(f"   Overall Quality: {scores.get('overall_quality', 'N/A')}/10")
            print(f"   Relevance: {scores.get('relevance_score', 'N/A')}/10")
            print(f"   Diversity: {scores.get('diversity_score', 'N/A')}/10")
            print(f"   Authority: {scores.get('authority_score', 'N/A')}/10")
            print(f"   Assessment: {scores.get('brief_assessment', 'N/A')}")
    
    # Display timing
    print(f"\n{Colors.BLUE}⏱️  Processing Time: {elapsed:.2f}s{Colors.ENDC}")
    
    # Summary
    print_section("CASE SUMMARY")
    gate_class = result.get('gate_decision', {}).get('output_class', 'unknown').upper()
    
    if gate_class == 'PRIMARY':
        print(f"{Colors.GREEN}✅ PRIMARY: Strong evidence found - authoritative response with citations{Colors.ENDC}")
    elif gate_class == 'HYBRID':
        print(f"{Colors.WARNING}⚠️ HYBRID: Partial evidence - bounded adjacent insight with limitations{Colors.ENDC}")
    elif gate_class in ['FULL_BACKUP', 'REFUSED']:
        print(f"{Colors.FAIL}🚫 {gate_class}: Insufficient/no evidence - deterministic refusal{Colors.ENDC}")
    else:
        print(f"{Colors.CYAN}ℹ️ Output Class: {gate_class}{Colors.ENDC}")
    
    return result


def main():
    """Run the three-case demo."""
    
    print_header("EVIDENCE INTELLIGENCE (EI) SYSTEM DEMO")
    print(f"""
    This demo shows three distinct outcomes based on evidence availability:
    
    🟢 CASE 1: Strong Evidence → PRIMARY + Citations
    🟡 CASE 2: Partial Evidence → HYBRID + Bounded Insight  
    🔴 CASE 3: No Evidence → REFUSE/FULL_BACKUP
    
    Architecture: Ingestion → Embedding → Deterministic Gating → Generation → Validation
    """)
    
    # Initialize the service
    print(f"\n{Colors.BLUE}Initializing EI Service...{Colors.ENDC}")
    service = interviewServicees()
    
    # Check if index has data
    stats = service.get_index_stats()
    print(f"Index Stats: {stats.get('total_vectors', 0)} vectors loaded")
    
    if stats.get('total_vectors', 0) == 0:
        print(f"\n{Colors.WARNING}⚠️ Index is empty! Loading interview files...{Colors.ENDC}")
        load_result = service.process_text_files_from_directory()
        print(f"Load Result: {load_result}")
        time.sleep(1)
    
    # ==========================================
    # CASE 1: Strong Evidence → PRIMARY
    # ==========================================
    # This question should match multiple CEO interviews about leadership/healthcare/scaling
    # Using broad leadership topic that appears in multiple interviews
    case1_question = (
        "What insights do CEOs share about building trust and creating value "
        "for their customers or patients in their organizations?"
    )
    result1 = run_demo_case(
        service, 1, case1_question,
        "Strong Evidence → PRIMARY Snapshot with Citations"
    )
    
    print("\n" + "="*80 + "\n")
    time.sleep(2)  # Pause between cases
    
    # ==========================================
    # CASE 2: Partial Evidence → HYBRID
    # ==========================================
    # This question has some relevance but limited direct matches
    case2_question = (
        "What strategies do executives use to balance innovation initiatives "
        "with day-to-day operational demands in their organizations?"
    )
    result2 = run_demo_case(
        service, 2, case2_question,
        "Partial Evidence → HYBRID Snapshot with Bounded Insight"
    )
    
    print("\n" + "="*80 + "\n")
    time.sleep(2)  # Pause between cases
    
    # ==========================================
    # CASE 3: No Evidence → REFUSE/FULL_BACKUP
    # ==========================================
    # This question is completely unrelated to the interview content
    case3_question = (
        "What are the best practices for implementing quantum computing "
        "algorithms in cryptocurrency mining operations?"
    )
    result3 = run_demo_case(
        service, 3, case3_question,
        "No Evidence → FULL_BACKUP/REFUSE Response"
    )
    
    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    print_header("DEMO SUMMARY: THREE CASES COMPARISON")
    
    print(f"""
    {Colors.BOLD}CASE 1 - Strong Evidence:{Colors.ENDC}
    ├─ Gate Decision: {result1.get('gate_decision', {}).get('output_class', 'N/A').upper()}
    ├─ Chunks Used: {result1.get('chunks_used', 0)}
    ├─ Citations: {len(result1.get('sources', []))}
    └─ Confidence: {result1.get('confidence_level', 'N/A')}
    
    {Colors.BOLD}CASE 2 - Partial Evidence:{Colors.ENDC}
    ├─ Gate Decision: {result2.get('gate_decision', {}).get('output_class', 'N/A').upper()}
    ├─ Chunks Used: {result2.get('chunks_used', 0)}
    ├─ Citations: {len(result2.get('sources', []))}
    └─ Confidence: {result2.get('confidence_level', 'N/A')}
    
    {Colors.BOLD}CASE 3 - No Evidence:{Colors.ENDC}
    ├─ Gate Decision: {result3.get('gate_decision', {}).get('output_class', 'N/A').upper()}
    ├─ Chunks Used: {result3.get('chunks_used', 0)}
    ├─ Citations: {len(result3.get('sources', []))}
    ├─ Flagged: {result3.get('flagged', False)}
    └─ Status: {result3.get('status', 'N/A')}
    """)
    
    print(f"""
{Colors.GREEN}✅ Demo Complete!{Colors.ENDC}

{Colors.BOLD}Key Architectural Points Demonstrated:{Colors.ENDC}

1. {Colors.CYAN}Deterministic Gating:{Colors.ENDC}
   - Gate decision is made BEFORE any LLM call
   - Based on hard thresholds (chunk count, similarity, unique sources)
   - Cannot be upgraded or overridden by LLM

2. {Colors.CYAN}Evidence Pack Construction:{Colors.ENDC}
   - Only chunks passing similarity threshold enter the pack
   - Citation tracking maintains source attribution
   - Metadata preserved for audit

3. {Colors.CYAN}Refusal/Downgrade Behavior:{Colors.ENDC}
   - FULL_BACKUP/REFUSED → No LLM strategy generation
   - Deterministic refusal message returned
   - System does not hallucinate authoritative content

4. {Colors.CYAN}Post-Generation Validation:{Colors.ENDC}
   - Claim ↔ Evidence alignment check
   - Generic strategy language detection
   - Fabrication detection and flagging

{Colors.BOLD}For a video demo, run this script and screen-record the output.{Colors.ENDC}
    """)


if __name__ == "__main__":
    main()
