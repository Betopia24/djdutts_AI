"""
Test script for the Interview Snapshot System
Demonstrates the three-tier snapshot logic with mandatory retrieval
"""

from app.services.interview.services import interviewServicees
import json
from datetime import datetime


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_snapshot_result(result, test_name):
    """Print formatted snapshot result"""
    print(f"\n📝 Test: {test_name}")
    print(f"   Snapshot Type: {result.get('snapshot_type', 'N/A').upper()}")
    print(f"   Chunks Used: {result.get('chunks_used', 0)}")
    print(f"   Top Score: {result.get('top_score', 0):.3f}")
    print(f"   Confidence: {result.get('confidence_level', 'N/A')}")
    print(f"   Retrieval Quality: {result.get('retrieval_quality', 'N/A')}")
    
    if result.get('flagged'):
        print(f"   ⚠️  FLAGGED: {result.get('warning', 'N/A')}")
    
    if result.get('sources'):
        print(f"\n   📚 Sources:")
        for i, source in enumerate(result['sources'][:3], 1):
            print(f"      {i}. {source.get('reference', 'N/A')} (score: {source.get('score', 0):.3f})")
    
    print(f"\n   💡 Answer Preview: {result.get('answer', '')[:200]}...")
    print(f"\n   📊 Retrieval Log:")
    log = result.get('retrieval_log', {})
    print(f"      - Timestamp: {log.get('timestamp', 'N/A')}")
    print(f"      - Chunks Retrieved: {log.get('chunks_retrieved', 0)}")
    print(f"      - Retrieval Time: {log.get('retrieval_time_seconds', 0):.3f}s")
    print("-" * 80)


def test_snapshot_system():
    """Test all three snapshot types"""
    
    print_section("Interview Snapshot System Test Suite")
    print("Testing mandatory retrieval and three-tier snapshot logic...\n")
    
    # Initialize service
    print("🔧 Initializing Interview Service...")
    service = interviewServicees()
    print("✅ Service initialized successfully\n")
    
    # Test 1: Interview-Based Snapshot (should get multiple chunks)
    print_section("TEST 1: Interview-Based Snapshot (≥2 chunks expected)")
    question1 = "How do you build and motivate high-performing teams?"
    result1 = service.interview_round(question1)
    print_snapshot_result(result1, "Team Leadership Question")
    
    # Test 2: Hybrid Snapshot (likely 1 chunk or partial match)
    print_section("TEST 2: Hybrid Snapshot (1 chunk or partial expected)")
    question2 = "What specific strategies do you use for innovation in healthcare technology?"
    result2 = service.interview_round(question2)
    print_snapshot_result(result2, "Specific Industry Question")
    
    # Test 3: Full Fallback Snapshot (should get 0 chunks)
    print_section("TEST 3: Full Fallback Snapshot (0 chunks expected - FLAGGED)")
    question3 = "What is the capital of France and its population?"
    result3 = service.interview_round(question3)
    print_snapshot_result(result3, "Unrelated Question")
    
    # Get retrieval logs
    print_section("Retrieval Logs (Recent)")
    logs = service.get_retrieval_logs(limit=5)
    for i, log in enumerate(logs, 1):
        print(f"{i}. [{log.get('timestamp', 'N/A')}]")
        print(f"   Question: {log.get('question', 'N/A')[:60]}...")
        print(f"   Chunks: {log.get('chunks_retrieved', 0)} | Top Score: {log.get('top_score', 0):.3f}")
        print()
    
    # Get snapshot statistics
    print_section("Snapshot Statistics")
    stats = service.get_snapshot_statistics()
    print(f"📈 Performance Metrics:")
    print(f"   Total Requests: {stats.get('total_requests', 0)}")
    print(f"   Successful Retrievals: {stats.get('successful_retrievals', 0)}")
    print(f"   High-Quality Retrievals: {stats.get('high_quality_retrievals', 0)}")
    print(f"   Retrieval Success Rate: {stats.get('retrieval_success_rate', 0)*100:.1f}%")
    print(f"   High-Quality Rate: {stats.get('high_quality_rate', 0)*100:.1f}%")
    print(f"   Zero-Chunk Requests: {stats.get('zero_chunk_requests', 0)}")
    
    # Get index statistics
    print_section("Vector Database Statistics")
    index_stats = service.get_index_stats()
    print(f"🗄️  Database Metrics:")
    print(f"   Total Vectors: {index_stats.get('total_vectors', 0)}")
    print(f"   Index Fullness: {index_stats.get('index_fullness', 0)*100:.2f}%")
    print(f"   Dimension: {index_stats.get('dimension', 0)}")
    
    print_section("Test Suite Complete")
    print("✅ All tests executed successfully")
    print("📋 Check logs above to verify:")
    print("   - All retrievals were logged")
    print("   - Snapshot types matched expected patterns")
    print("   - Fallback was properly flagged")
    print("\n" + "="*80 + "\n")


def test_individual_question(question: str):
    """Test a single question and display detailed results"""
    
    print_section(f"Testing Question")
    print(f"❓ Question: {question}\n")
    
    service = interviewServicees()
    result = service.interview_round(question)
    
    print(f"📊 Results:")
    print(json.dumps(result, indent=2, default=str))
    
    print_section("Test Complete")


if __name__ == "__main__":
    # Run full test suite
    test_snapshot_system()
    
    # Uncomment to test individual questions:
    # test_individual_question("How do you handle difficult conversations with employees?")
