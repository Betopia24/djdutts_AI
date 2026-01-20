# Interview Snapshot System - Quick Reference

## 🎯 Core Rules

1. ✅ **MANDATORY RETRIEVAL** - Every snapshot MUST start with vector database retrieval
2. ✅ **ALWAYS LOGGED** - Every retrieval is logged (success or failure)
3. ✅ **INTERVIEW-FIRST** - Interview dataset is the primary intelligence source
4. ❌ **NO BYPASS** - No snapshot may skip retrieval step
5. ❌ **NO AI OVERRIDE** - AI cannot replace leadership logic from interviews

---

## 📊 Snapshot Decision Tree

```
Retrieval Result
    │
    ├─ ≥2 chunks with score ≥0.75
    │  └─→ INTERVIEW-BASED SNAPSHOT (High Confidence)
    │
    ├─ 1 chunk OR <2 high-quality chunks
    │  └─→ HYBRID SNAPSHOT (Medium Confidence)
    │
    └─ 0 chunks
       └─→ FULL FALLBACK SNAPSHOT ⚠️ FLAGGED (Low Confidence)
```

---

## 🔍 Snapshot Types at a Glance

| Type | Chunks | Quality | AI Role | Confidence | Flagged |
|------|--------|---------|---------|------------|---------|
| **Interview-Based** | ≥2 | High (≥0.75) | Synthesis only | High | No |
| **Hybrid** | 1 or insufficient | Partial | Complete gaps | Medium | No |
| **Full Fallback** | 0 | None | Full generation | Low | Yes ⚠️ |

---

## 💻 Code Examples

### Basic Usage
```python
from app.services.interview.services import interviewServicees

service = interviewServicees()
result = service.interview_round("How do you motivate teams?")

print(f"Snapshot Type: {result['snapshot_type']}")
print(f"Chunks Used: {result['chunks_used']}")
print(f"Answer: {result['answer']}")
```

### Check Snapshot Type
```python
from app.services.interview.services import SnapshotType

if result['snapshot_type'] == SnapshotType.INTERVIEW_BASED.value:
    print("✅ High-quality interview-based response")
elif result['snapshot_type'] == SnapshotType.HYBRID.value:
    print("⚠️ Hybrid response - partial interview data")
elif result['snapshot_type'] == SnapshotType.FULL_FALLBACK.value:
    print("🚨 Fallback response - no interview data found")
```

### Monitor Retrieval
```python
# Get recent retrieval logs
logs = service.get_retrieval_logs(limit=10)

for log in logs:
    print(f"{log['timestamp']}: {log['chunks_retrieved']} chunks retrieved")
```

### Check System Health
```python
# Get snapshot statistics
stats = service.get_snapshot_statistics()

print(f"Retrieval Success Rate: {stats['retrieval_success_rate']*100:.1f}%")
print(f"High-Quality Rate: {stats['high_quality_rate']*100:.1f}%")
print(f"Fallback Requests: {stats['zero_chunk_requests']}")

# Alert if fallback rate is high
fallback_rate = stats['zero_chunk_requests'] / stats['total_requests']
if fallback_rate > 0.20:  # 20% threshold
    print("⚠️ High fallback rate - consider expanding database")
```

---

## 🌐 API Quick Reference

### Interview Round
```bash
POST /interview_round
Content-Type: application/json

{
  "question": "How do you handle team conflicts?"
}
```

**Response Fields**:
- `snapshot_type`: interview_based | hybrid | full_fallback
- `chunks_used`: Number of chunks used
- `confidence_level`: high | medium | low
- `retrieval_quality`: excellent | partial | none
- `flagged`: true (only for full_fallback)

### Get Retrieval Logs
```bash
GET /retrieval_logs?limit=10
```

### Get Statistics
```bash
GET /snapshot_statistics
```

---

## 🎨 Response Examples

### ✅ Interview-Based (Best Case)
```json
{
  "snapshot_type": "interview_based",
  "chunks_used": 3,
  "top_score": 0.89,
  "confidence_level": "high",
  "retrieval_quality": "excellent",
  "sources": [
    {"type": "ceo_interview", "reference": "Alexis Nasard", "score": 0.89}
  ],
  "answer": "Based on insights from Alexis Nasard (CEO at L'Oréal)..."
}
```

### ⚠️ Hybrid (Partial Match)
```json
{
  "snapshot_type": "hybrid",
  "chunks_used": 1,
  "top_score": 0.72,
  "confidence_level": "medium",
  "retrieval_quality": "partial",
  "note": "Interview-first response with AI structural completion",
  "answer": "Drawing from Paul Keel's experience, combined with frameworks..."
}
```

### 🚨 Full Fallback (No Match)
```json
{
  "snapshot_type": "full_fallback",
  "chunks_used": 0,
  "top_score": 0.0,
  "confidence_level": "low",
  "retrieval_quality": "none",
  "flagged": true,
  "warning": "⚠️ No interview data available - pure AI fallback",
  "answer": "While no specific executive insights are available..."
}
```

---

## 🔧 Configuration

### Thresholds (in services.py)
```python
self.min_chunks_for_interview_based = 2        # Minimum chunks for interview-based
self.min_score_for_sufficient_insight = 0.75   # Minimum score for high quality
self.confidence_threshold = 0.7                # General confidence threshold
```

### Tuning Guidelines
- **Increase** `min_score_for_sufficient_insight` → More hybrid snapshots, fewer interview-based
- **Decrease** `min_chunks_for_interview_based` → More interview-based snapshots
- Monitor statistics and adjust based on your quality requirements

---

## 📈 Monitoring Checklist

Daily:
- [ ] Check retrieval success rate (target: >80%)
- [ ] Review flagged responses
- [ ] Monitor average retrieval time

Weekly:
- [ ] Analyze common fallback questions
- [ ] Review high-quality rate (target: >60%)
- [ ] Check for new interview content needs

Monthly:
- [ ] Audit retrieval logs for patterns
- [ ] Tune thresholds based on performance
- [ ] Expand database with new interviews

---

## 🚨 Troubleshooting

### High Fallback Rate (>20%)
- **Cause**: Insufficient interview content for common questions
- **Fix**: Add more interview files covering missing topics

### Low High-Quality Rate (<40%)
- **Cause**: Chunks not specific enough or embedding quality issues
- **Fix**: Review chunking strategy, improve interview content structure

### Slow Retrieval (>1s)
- **Cause**: Index performance or network issues
- **Fix**: Check Pinecone index settings, consider caching

---

## 📚 Files Modified

- [services.py](app/services/interview/services.py) - Core RAG logic
- [schema.py](app/services/interview/schema.py) - Response models
- [route.py](app/services/interview/route.py) - API endpoints
- [SNAPSHOT_SYSTEM.md](SNAPSHOT_SYSTEM.md) - Detailed documentation
- [test_snapshot_system.py](test_snapshot_system.py) - Test suite

---

**Last Updated**: January 16, 2026  
**System Version**: 1.0
