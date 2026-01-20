# Interview Snapshot System - RAG Implementation

## Overview
This system implements a **Retrieval-Augmented Generation (RAG)** approach for interview-based responses with **mandatory retrieval** and comprehensive logging.

## Core Principles

### 1. **Interview Dataset as Primary Intelligence Source**
- All interview text files are clean and ready for chunking
- Interview insights take precedence over AI generation
- Leadership wisdom from real executives is preserved

### 2. **Mandatory Retrieval**
- **EVERY snapshot MUST begin with retrieval from the vector database**
- **NO snapshot may bypass retrieval**
- All retrieval attempts are logged (success or failure)

### 3. **Comprehensive Logging**
- Every retrieval is logged with:
  - Timestamp
  - Question asked
  - Number of chunks retrieved
  - Top relevance score
  - Retrieval time
  - Chunk IDs

## Snapshot Types

### 🟢 Interview-Based Snapshot (≥2 chunks)
**Trigger**: When **2 or more high-quality chunks** are retrieved

**Characteristics**:
- Pure interview-driven response
- Synthesizes insights from multiple executive interviews
- No AI completion - only synthesis of existing content
- Cites specific sources (executives, companies)
- **Highest confidence and quality**

**Example**:
```json
{
  "snapshot_type": "interview_based",
  "chunks_used": 3,
  "confidence_level": "high",
  "retrieval_quality": "excellent",
  "sources": [
    {"type": "ceo_interview", "reference": "Paul Keel", "score": 0.89},
    {"type": "ceo_interview", "reference": "Alexis Nasard", "score": 0.85}
  ]
}
```

### 🟡 Hybrid Snapshot (1 chunk OR insufficient insight)
**Trigger**: When **1 chunk is retrieved** OR **multiple chunks lack sufficient insight**

**Characteristics**:
- Interview-First: Starts with available interview data
- AI-Completed: Fills structural gaps only
- AI **may NOT replace leadership logic**
- AI provides framework, examples, or application guidance
- **Medium confidence**

**Example**:
```json
{
  "snapshot_type": "hybrid",
  "chunks_used": 1,
  "confidence_level": "medium",
  "retrieval_quality": "partial",
  "note": "Interview-first response with AI structural completion"
}
```

### 🔴 Full Fallback Snapshot (0 chunks) - **FLAGGED**
**Trigger**: When **0 chunks are retrieved**

**Characteristics**:
- Pure AI generation
- **Automatically FLAGGED**
- Clear warning in response
- Acknowledges lack of interview data
- Suggests database expansion or query refinement
- **Low confidence**

**Example**:
```json
{
  "snapshot_type": "full_fallback",
  "chunks_used": 0,
  "confidence_level": "low",
  "retrieval_quality": "none",
  "flagged": true,
  "warning": "⚠️ No interview data available - pure AI fallback",
  "note": "Consider expanding interview database or refining query"
}
```

## System Architecture

### Flow Diagram
```
User Question
     ↓
MANDATORY RETRIEVAL (ALWAYS LOGGED)
     ↓
Chunk Count Analysis
     ↓
     ├─→ ≥2 chunks + high quality → INTERVIEW-BASED SNAPSHOT
     │
     ├─→ 1 chunk OR insufficient → HYBRID SNAPSHOT
     │
     └─→ 0 chunks → FULL FALLBACK SNAPSHOT (FLAGGED)
```

### Key Thresholds
```python
min_chunks_for_interview_based = 2
min_score_for_sufficient_insight = 0.75
confidence_threshold = 0.7
```

## API Endpoints

### POST `/interview_round`
Main endpoint for generating snapshots.

**Request**:
```json
{
  "question": "How do you handle team conflicts?"
}
```

**Response**:
```json
{
  "status": "success",
  "snapshot_type": "interview_based",
  "question": "How do you handle team conflicts?",
  "answer": "Based on insights from multiple executives...",
  "chunks_used": 3,
  "top_score": 0.89,
  "ei_competencies": ["social_skills", "empathy", "leadership"],
  "sources": [...],
  "confidence_level": "high",
  "retrieval_quality": "excellent",
  "retrieval_log": {
    "timestamp": "2026-01-16T10:30:00",
    "chunks_retrieved": 3,
    "top_score": 0.89
  }
}
```

### GET `/retrieval_logs?limit=10`
Retrieves recent retrieval logs for monitoring.

**Response**:
```json
{
  "status": "success",
  "logs": [
    {
      "timestamp": "2026-01-16T10:30:00",
      "question": "How do you handle team conflicts?",
      "chunks_retrieved": 3,
      "top_score": 0.89,
      "retrieval_time_seconds": 0.234
    }
  ]
}
```

### GET `/snapshot_statistics`
Gets aggregate statistics about snapshot generation.

**Response**:
```json
{
  "total_requests": 100,
  "successful_retrievals": 87,
  "high_quality_retrievals": 65,
  "retrieval_success_rate": 0.87,
  "high_quality_rate": 0.65,
  "zero_chunk_requests": 13
}
```

## Logging Examples

### 🔍 Retrieval Log Entry
```
2026-01-16 10:30:00 - interview.services - INFO - 🔍 RETRIEVAL LOG: {
  "timestamp": "2026-01-16T10:30:00",
  "question": "How do you motivate teams?",
  "chunks_retrieved": 4,
  "top_score": 0.91,
  "retrieval_time_seconds": 0.187,
  "chunk_ids": ["interview_35_antje_lochmann", "interview_21_sangita_reddy", ...]
}
```

### 📊 Snapshot Creation Log
```
2026-01-16 10:30:01 - interview.services - INFO - 📊 Creating INTERVIEW-BASED Snapshot (4 chunks)
2026-01-16 10:30:03 - interview.services - INFO - ✅ Snapshot complete: interview_based | Chunks: 4 | Confidence: high
```

### ⚠️ Fallback Warning Log
```
2026-01-16 10:35:00 - interview.services - WARNING - ⚠️ Creating FULL FALLBACK Snapshot (0 chunks - FLAGGED)
```

## AI Guardrails

### ✅ AI MAY:
- Synthesize multiple interview insights
- Structure information clearly
- Add frameworks (STAR method, etc.)
- Provide examples when interviews lack them
- Complete structural gaps in hybrid snapshots

### ❌ AI MAY NOT:
- Replace leadership logic from interviews
- Contradict executive insights
- Invent interview content
- Bypass retrieval
- Generate responses without attempting retrieval

## Monitoring & Maintenance

### Key Metrics to Track:
1. **Retrieval Success Rate**: % of requests with >0 chunks
2. **High-Quality Rate**: % of requests with ≥2 chunks + score ≥0.75
3. **Fallback Rate**: % of requests requiring full fallback
4. **Average Retrieval Time**: Performance metric
5. **Top Score Distribution**: Quality of matches

### When to Expand Database:
- High fallback rate (>20%)
- Low average top scores (<0.6)
- Frequent hybrid snapshots with single chunks
- Common question patterns not matched

## Code Structure

### Main Files:
- **[services.py](app/services/interview/services.py)**: Core RAG logic and snapshot generation
- **[schema.py](app/services/interview/schema.py)**: Pydantic models for requests/responses
- **[route.py](app/services/interview/route.py)**: FastAPI endpoints

### Key Methods:

#### `_mandatory_retrieval(question, top_k=5)`
- Performs vector search
- Logs all retrieval attempts
- Returns chunks with metadata

#### `_create_interview_based_snapshot(question, chunks)`
- Synthesizes ≥2 high-quality chunks
- Pure interview-driven response

#### `_create_hybrid_snapshot(question, chunks)`
- Interview-first approach
- AI completes structural gaps only

#### `_create_full_fallback_snapshot(question)`
- Pure AI generation
- Automatically flagged
- Includes warning

#### `interview_round(question)`
- Main entry point
- Orchestrates retrieval and snapshot selection
- Returns comprehensive response

## Best Practices

1. **Always Check Logs**: Review retrieval logs regularly
2. **Monitor Fallback Rate**: High rates indicate database gaps
3. **Quality Over Quantity**: 2 high-quality chunks > 5 low-quality chunks
4. **Update Interview Database**: Add new interviews when patterns emerge
5. **Tune Thresholds**: Adjust based on your specific use case
6. **Review Flagged Responses**: All fallbacks are opportunities to improve

## Environment Variables Required

```env
PINECONE_API_KEY=your_pinecone_api_key
GOOGLE_AI_API_KEY=your_google_ai_api_key
```

## Testing

### Test Interview-Based Snapshot:
```python
# Question that should match multiple interviews
response = interview_service.interview_round(
    "How do you build high-performing teams?"
)
assert response["snapshot_type"] == "interview_based"
assert response["chunks_used"] >= 2
```

### Test Hybrid Snapshot:
```python
# Very specific question likely to match 1 chunk
response = interview_service.interview_round(
    "What's your experience with AI in healthcare manufacturing?"
)
assert response["snapshot_type"] == "hybrid"
```

### Test Full Fallback:
```python
# Completely unrelated question
response = interview_service.interview_round(
    "What's the weather like in Antarctica?"
)
assert response["snapshot_type"] == "full_fallback"
assert response["flagged"] == True
```

## Future Enhancements

1. **Chunk Quality Scoring**: Beyond cosine similarity
2. **Multi-Index Support**: Separate indexes for different content types
3. **Retrieval Caching**: Cache common queries
4. **A/B Testing**: Compare snapshot types
5. **User Feedback Loop**: Learn from user ratings
6. **Dynamic Thresholds**: Adjust based on performance
7. **Semantic Chunking**: Better chunk boundaries

---

**Version**: 1.0  
**Last Updated**: January 16, 2026  
**Maintained By**: Interview Intelligence Team
