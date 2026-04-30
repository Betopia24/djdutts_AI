#!/usr/bin/env python3
"""
DETERMINISTIC GATING & EI VALIDATION SCRIPT

This script validates the deterministic gating and EI behavior by testing:

1. PRIMARY example:
   - ≥2 interviews
   - ≥2 chunks  
   - snapshot_type = "primary" or "interview_based"
   - citations included

2. FULL_BACKUP / REFUSE example:
   - No relevant chunks
   - snapshot_type = "full_backup" or "refused"
   - No authoritative strategy language
   - Structured citation metadata in the response

Author: GitHub Copilot
Date: February 15, 2026
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.services.interview.services import interviewServicees

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeterministicGatingValidator:
    """Validates the deterministic gating and EI behavior of the interview service."""
    
    def __init__(self):
        self.service = interviewServicees()
        self.validation_results = []
        
    def print_section_header(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}")
        
    def print_subsection_header(self, title: str):
        """Print a formatted subsection header."""
        print(f"\n{'-' * 60}")
        print(f"  {title}")
        print(f"{'-' * 60}")
        
    def setup_index(self):
        """Setup the FAISS index with interview data."""
        self.print_section_header("SETTING UP INTERVIEW INDEX")
        
        print("🔄 Processing interview files...")
        result = self.service.process_text_files_from_directory()
        
        if result.get('status') == 'success':
            print(f"✅ Success: {result['files_processed']} files processed")
            print(f"📊 Total vectors in index: {result['total_vectors']}")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
            return False
            
        # Get index stats
        stats = self.service.get_index_stats()
        print(f"📈 Index Statistics:")
        print(f"   - Total vectors: {stats.get('total_vectors', 0)}")
        print(f"   - Dimension: {stats.get('dimension', 0)}")
        print(f"   - Metadata entries: {stats.get('metadata_entries', 0)}")
        
        return True
        
    def format_citation_metadata(self, response: dict) -> dict:
        """Extract and format structured citation metadata."""
        citations = {
            'interviews_cited': [],
            'chunks_used': response.get('chunks_used', 0),
            'top_similarity_score': response.get('top_score', 0.0),
            'unique_executives': set(),
            'citation_details': []
        }
        
        # Extract citation information from sources
        sources = response.get('sources', [])
        gate_decision = response.get('gate_decision', {})
        
        for i, source in enumerate(sources):
            citation = {
                'chunk_id': f"chunk_{i+1}",
                'interview_id': f"interview_{source.get('reference', 'unknown').replace(' ', '_').lower()}",
                'executive_name': source.get('reference', 'Unknown'),
                'similarity_score': source.get('score', 0.0),
                'source_type': source.get('type', 'unknown')
            }
            citations['citation_details'].append(citation)
            citations['unique_executives'].add(citation['executive_name'])
        
        # Add gate decision metadata
        citations['gate_metadata'] = {
            'output_class': gate_decision.get('output_class', 'unknown'),
            'chunks_passed_gate': gate_decision.get('chunks_passed_gate', 0),
            'unique_interviews': gate_decision.get('unique_interviews', 0),
            'deterministic_decision': gate_decision.get('is_deterministic', False),
            'decision_reason': gate_decision.get('reason', 'No reason provided')
        }
        
        return citations

    def format_response_audit(self, response: dict) -> dict:
        """Extract the audit fields requested for each example."""
        validation = response.get('validation', {})
        return {
            'query': response.get('question', ''),
            'output_class': response.get('output_class', 'unknown'),
            'llm_called': response.get('llm_called', None),
            'llm_blocked': response.get('llm_blocked', None),
            'retrieval_count': response.get('retrieval_count', response.get('chunks_used', 0)),
            'unique_interviews': response.get('unique_interviews', response.get('evidence_summary', {}).get('unique_interviews', 0)),
            'similarity_scores': response.get('similarity_scores', [source.get('similarity_score', 0.0) for source in response.get('sources', [])]),
            'gate_decision': response.get('gate_decision', {}),
            'validation_result': response.get('validation_result', validation),
            'downgrade_applied': response.get('downgrade_applied', validation.get('auto_downgrade_applied')),
            'source_references': response.get('sources', []),
            'final_response': response.get('answer', '')
        }

    def print_response_audit(self, response: dict):
        """Print the requested audit fields in a compact block."""
        audit = self.format_response_audit(response)
        gate_decision = audit['gate_decision']
        validation_result = audit['validation_result'] or {}

        self.print_subsection_header("RESPONSE AUDIT")
        print(f"Query: {audit['query']}")
        print(f"Output Class: {audit['output_class']}")
        print(f"LLM Called: {audit['llm_called']}")
        print(f"LLM Blocked: {audit['llm_blocked']}")
        print(f"Retrieval Count: {audit['retrieval_count']}")
        print(f"Unique Interview Count: {audit['unique_interviews']}")
        print(f"Similarity Scores: {audit['similarity_scores']}")
        print(f"Gate Decision: {gate_decision.get('output_class', 'unknown')} - {gate_decision.get('reason', 'N/A')}")
        print(f"Validation Result: {validation_result}")
        print(f"Downgrade Applied: {audit['downgrade_applied'] or 'None'}")
        print(f"Source References: {len(audit['source_references'])} source(s)")
        for i, source in enumerate(audit['source_references'], 1):
            print(
                f"  {i}. {source.get('executive_name', 'Unknown')} | "
                f"{source.get('interview_id', 'N/A')} | {source.get('chunk_id', 'N/A')} | "
                f"score={source.get('similarity_score', 0.0):.3f}"
            )
        print("Final Response Returned:")
        print(audit['final_response'])
        
    def test_primary_example(self):
        """Test PRIMARY output class with ≥2 interviews and ≥2 chunks."""
        self.print_section_header("PRIMARY EXAMPLE VALIDATION")
        
        # Test query about leadership and innovation (should match multiple CEO interviews)
        test_query = "How do successful CEOs approach innovation and team building in their organizations?"
        
        print(f"🎯 Test Query: {test_query}")
        print(f"🎯 Expected Outcome: PRIMARY class with ≥2 chunks from ≥2 interviews")
        
        self.print_subsection_header("EXECUTING QUERY")
        
        # Execute query with LLM scoring enabled
        response = self.service.interview_round(test_query, enable_llm_scoring=True)
        
        # Extract key metrics
        output_class = response.get('output_class', 'unknown')
        snapshot_type = response.get('snapshot_type', 'unknown')
        chunks_used = response.get('chunks_used', 0)
        gate_decision = response.get('gate_decision', {})
        unique_interviews = gate_decision.get('unique_interviews', 0)
        
        self.print_subsection_header("RESPONSE ANALYSIS")
        
        print(f"📊 Output Class: {output_class.upper()}")
        print(f"📊 Snapshot Type: {snapshot_type}")
        print(f"📊 Chunks Used: {chunks_used}")
        print(f"📊 Unique Interviews: {unique_interviews}")
        print(f"📊 Top Similarity Score: {response.get('top_score', 0.0):.3f}")
        
        # Validate PRIMARY criteria
        is_primary = output_class.lower() == 'primary'
        has_sufficient_chunks = chunks_used >= 2
        has_multiple_interviews = unique_interviews >= 2
        
        print(f"\n✓ PRIMARY Class: {'✅ PASS' if is_primary else '❌ FAIL'}")
        print(f"✓ ≥2 Chunks: {'✅ PASS' if has_sufficient_chunks else '❌ FAIL'}")
        print(f"✓ ≥2 Interviews: {'✅ PASS' if has_multiple_interviews else '❌ FAIL'}")
        
        # Extract and display structured citation metadata
        self.print_subsection_header("STRUCTURED CITATION METADATA")
        
        citations = self.format_citation_metadata(response)
        
        print(f"📚 Citation Summary:")
        print(f"   - Chunks Used: {citations['chunks_used']}")
        print(f"   - Unique Executives: {len(citations['unique_executives'])}")
        print(f"   - Top Similarity: {citations['top_similarity_score']:.3f}")
        
        print(f"\n📖 Detailed Citations:")
        for cite in citations['citation_details']:
            print(f"   • Interview ID: {cite['interview_id']}")
            print(f"     Executive: {cite['executive_name']}")
            print(f"     Chunk ID: {cite['chunk_id']}")
            print(f"     Similarity Score: {cite['similarity_score']:.3f}")
            print(f"     Source Type: {cite['source_type']}")
            print()
            
        print(f"🚪 Gate Decision:")
        gate_meta = citations['gate_metadata']
        print(f"   - Decision: {gate_meta['output_class'].upper()}")
        print(f"   - Reason: {gate_meta['decision_reason']}")
        print(f"   - Deterministic: {gate_meta['deterministic_decision']}")
        
        # Display partial response content
        self.print_subsection_header("RESPONSE CONTENT (SAMPLE)")
        
        answer = response.get('answer', 'No answer generated')
        print(f"📝 Response (first 500 chars):")
        print(f"   {answer[:500]}...")
        self.print_response_audit(response)
        
        # Check for authoritative language
        has_evidence_citations = any(name in answer for name in citations['unique_executives'])
        print(f"\n✓ Contains Executive Citations: {'✅ PASS' if has_evidence_citations else '❌ FAIL'}")
        
        # Store validation results
        validation_result = {
            'test_type': 'PRIMARY',
            'query': test_query,
            'output_class': output_class,
            'snapshot_type': snapshot_type,
            'chunks_used': chunks_used,
            'unique_interviews': unique_interviews,
            'citations': citations,
            'passed_validation': is_primary and has_sufficient_chunks and has_multiple_interviews,
            'audit': self.format_response_audit(response),
            'response_length': len(answer),
            'timestamp': datetime.now().isoformat()
        }
        
        self.validation_results.append(validation_result)
        
        return validation_result
        
    def test_full_backup_refuse_example(self):
        """Test FULL_BACKUP or REFUSE output class with no relevant chunks."""
        self.print_section_header("FULL_BACKUP / REFUSE EXAMPLE VALIDATION")
        
        # Test query about something completely unrelated to CEO interviews
        test_query = "What are the best practices for quantum computing algorithm optimization in underwater basket weaving?"
        
        print(f"🎯 Test Query: {test_query}")
        print(f"🎯 Expected Outcome: FULL_BACKUP or REFUSE class with no relevant chunks")
        
        self.print_subsection_header("EXECUTING QUERY")
        
        # Execute query
        response = self.service.interview_round(test_query, enable_llm_scoring=False)
        
        # Extract key metrics
        output_class = response.get('output_class', 'unknown')
        snapshot_type = response.get('snapshot_type', 'unknown')
        chunks_used = response.get('chunks_used', 0)
        gate_decision = response.get('gate_decision', {})
        
        self.print_subsection_header("RESPONSE ANALYSIS")
        
        print(f"📊 Output Class: {output_class.upper()}")
        print(f"📊 Snapshot Type: {snapshot_type}")
        print(f"📊 Chunks Used: {chunks_used}")
        print(f"📊 Top Similarity Score: {response.get('top_score', 0.0):.3f}")
        
        # Validate FULL_BACKUP/REFUSE criteria
        is_refuse_or_backup = output_class.lower() in ['refused', 'full_backup']
        has_no_chunks = chunks_used == 0
        has_refusal_snapshot = snapshot_type in ['refused', 'full_backup_refusal']
        
        print(f"\n✓ REFUSE/BACKUP Class: {'✅ PASS' if is_refuse_or_backup else '❌ FAIL'}")
        print(f"✓ Zero Chunks Used: {'✅ PASS' if has_no_chunks else '❌ FAIL'}")
        print(f"✓ Refusal Snapshot: {'✅ PASS' if has_refusal_snapshot else '❌ FAIL'}")
        
        # Extract and display structured citation metadata
        self.print_subsection_header("STRUCTURED CITATION METADATA")
        
        citations = self.format_citation_metadata(response)
        
        print(f"📚 Citation Summary:")
        print(f"   - Chunks Used: {citations['chunks_used']}")
        print(f"   - Unique Executives: {len(citations['unique_executives'])}")
        print(f"   - Top Similarity: {citations['top_similarity_score']:.3f}")
        
        print(f"🚪 Gate Decision:")
        gate_meta = citations['gate_metadata']
        print(f"   - Decision: {gate_meta['output_class'].upper()}")
        print(f"   - Reason: {gate_meta['decision_reason']}")
        print(f"   - Deterministic: {gate_meta['deterministic_decision']}")
        
        # Display response content
        self.print_subsection_header("RESPONSE CONTENT")
        
        answer = response.get('answer', 'No answer generated')
        print(f"📝 Response:")
        print(f"   {answer}")
        self.print_response_audit(response)
        
        # Check for authoritative language (should be absent)
        has_authoritative_language = any(phrase in answer.lower() for phrase in [
            'best practice', 'industry standard', 'proven strategy', 
            'expert recommendation', 'comprehensive approach'
        ])
        
        has_refusal_language = any(phrase in answer.lower() for phrase in [
            'unable to provide', 'cannot provide', 'insufficient', 
            'no evidence', 'no relevant', 'refusal'
        ])
        
        print(f"\n✓ No Authoritative Language: {'✅ PASS' if not has_authoritative_language else '❌ FAIL'}")
        print(f"✓ Contains Refusal Language: {'✅ PASS' if has_refusal_language else '❌ FAIL'}")
        
        # Store validation results
        validation_result = {
            'test_type': 'FULL_BACKUP_REFUSE',
            'query': test_query,
            'output_class': output_class,
            'snapshot_type': snapshot_type,
            'chunks_used': chunks_used,
            'citations': citations,
            'passed_validation': is_refuse_or_backup and has_no_chunks,
            'audit': self.format_response_audit(response),
            'has_authoritative_language': has_authoritative_language,
            'has_refusal_language': has_refusal_language,
            'response_length': len(answer),
            'timestamp': datetime.now().isoformat()
        }
        
        self.validation_results.append(validation_result)
        
        return validation_result
        
    def test_edge_case_hybrid(self):
        """Test HYBRID output class edge case."""
        self.print_section_header("HYBRID EXAMPLE (EDGE CASE)")
        
        # Test query that might match one good chunk but not enough for PRIMARY
        test_query = "What specific experience does Sangita Reddy have with healthcare insurance?"
        
        print(f"🎯 Test Query: {test_query}")
        print(f"🎯 Expected Outcome: Potentially HYBRID class (1 strong chunk)")
        
        response = self.service.interview_round(test_query, enable_llm_scoring=True)
        
        output_class = response.get('output_class', 'unknown')
        snapshot_type = response.get('snapshot_type', 'unknown')
        chunks_used = response.get('chunks_used', 0)
        
        print(f"📊 Output Class: {output_class.upper()}")
        print(f"📊 Snapshot Type: {snapshot_type}")
        print(f"📊 Chunks Used: {chunks_used}")
        print(f"📊 Top Similarity Score: {response.get('top_score', 0.0):.3f}")
        
        citations = self.format_citation_metadata(response)
        print(f"\n📖 Executive Citations: {list(citations['unique_executives'])}")
        
        return response
        
    def generate_summary_report(self):
        """Generate a summary report of all validation tests."""
        self.print_section_header("VALIDATION SUMMARY REPORT")
        
        print(f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total Tests: {len(self.validation_results)}")
        
        passed_tests = sum(1 for result in self.validation_results if result.get('passed_validation', False))
        print(f"✅ Tests Passed: {passed_tests}/{len(self.validation_results)}")
        
        self.print_subsection_header("TEST DETAILS")
        
        for i, result in enumerate(self.validation_results, 1):
            status = "✅ PASS" if result.get('passed_validation', False) else "❌ FAIL"
            print(f"{i}. {result['test_type']}: {status}")
            print(f"   Query: {result['query'][:80]}...")
            print(f"   Output Class: {result['output_class'].upper()}")
            print(f"   Chunks Used: {result['chunks_used']}")
            if result.get('unique_interviews'):
                print(f"   Unique Interviews: {result['unique_interviews']}")
            print()
            
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"validation_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump({
                'validation_summary': {
                    'total_tests': len(self.validation_results),
                    'passed_tests': passed_tests,
                    'timestamp': datetime.now().isoformat()
                },
                'test_results': self.validation_results
            }, f, indent=2)
            
        print(f"📄 Detailed report saved to: {report_file}")
        
    def run_complete_validation(self):
        """Run the complete validation suite."""
        print("🚀 Starting Deterministic Gating & EI Validation")
        print(f"🕒 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Setup
        if not self.setup_index():
            print("❌ Failed to setup index. Aborting validation.")
            return False
            
        # Test cases
        try:
            self.test_primary_example()
            self.test_full_backup_refuse_example()
            self.test_edge_case_hybrid()
            
            # Generate summary
            self.generate_summary_report()
            
            print("\n🎉 Validation suite completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation failed with error: {e}")
            print(f"\n❌ Validation failed: {e}")
            return False

def main():
    """Main entry point for validation script."""
    validator = DeterministicGatingValidator()
    success = validator.run_complete_validation()
    
    if success:
        print("\n✅ All validations completed. Check the generated report for detailed results.")
    else:
        print("\n❌ Validation failed. Please check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()