# Pre-Deployment Checklist

## ✅ Implementation Verification

### 1. Code Files
- [ ] [services.py](app/services/interview/services.py) - Core RAG logic implemented
- [ ] [schema.py](app/services/interview/schema.py) - New response models added
- [ ] [route.py](app/services/interview/route.py) - API endpoints updated
- [ ] All files error-free (syntax check passed)

### 2. Core Features
- [ ] `_mandatory_retrieval()` method implemented
- [ ] `_create_interview_based_snapshot()` method implemented
- [ ] `_create_hybrid_snapshot()` method implemented
- [ ] `_create_full_fallback_snapshot()` method implemented
- [ ] `interview_round()` updated with three-tier logic
- [ ] `get_retrieval_logs()` method added
- [ ] `get_snapshot_statistics()` method added

### 3. Documentation
- [ ] [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Complete overview
- [ ] [SNAPSHOT_SYSTEM.md](SNAPSHOT_SYSTEM.md) - Detailed documentation
- [ ] [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick reference guide
- [ ] [ARCHITECTURE.txt](ARCHITECTURE.txt) - Visual architecture diagram

### 4. Testing
- [ ] [test_snapshot_system.py](test_snapshot_system.py) - Test suite created

---

## 🚀 Deployment Steps

### Step 1: Environment Setup
```bash
# Verify environment variables
echo $PINECONE_API_KEY
echo $GOOGLE_AI_API_KEY
```
- [ ] Pinecone API key configured
- [ ] Google AI API key configured

### Step 2: Load Interview Data
```bash
# Option A: Via API (if server running)
curl -X POST http://localhost:8000/load_interview_files

# Option B: Via Python
python -c "from app.services.interview.services import interviewServicees; s = interviewServicees(); s.process_text_files_from_directory()"
```
- [ ] Interview files loaded into Pinecone
- [ ] Vector count verified (should be ~30)

### Step 3: Load Q&A Dataset
```bash
# Option A: Via API
curl -X POST http://localhost:8000/load_qa_dataset

# Option B: Via Python
python -c "from app.services.interview.services import interviewServicees; s = interviewServicees(); s.process_qa_dataset()"
```
- [ ] Q&A dataset loaded into Pinecone
- [ ] Vector count verified (should be ~100+)

### Step 4: Run Test Suite
```bash
python test_snapshot_system.py
```
- [ ] Test suite runs without errors
- [ ] All three snapshot types demonstrated
- [ ] Retrieval logs displayed
- [ ] Statistics calculated correctly

### Step 5: Start API Server
```bash
uvicorn main:app --reload
```
- [ ] Server starts successfully
- [ ] No import errors
- [ ] API docs accessible at http://localhost:8000/docs

---

## 🧪 Functional Testing

### Test 1: Interview-Based Snapshot (Expected)
```bash
curl -X POST http://localhost:8000/interview_round \
  -H "Content-Type: application/json" \
  -d '{"question": "How do you build and lead high-performing teams?"}'
```
**Expected Result**:
- [ ] `snapshot_type`: "interview_based"
- [ ] `chunks_used`: ≥2
- [ ] `confidence_level`: "high"
- [ ] `retrieval_quality`: "excellent"
- [ ] Sources include executive names

### Test 2: Hybrid Snapshot (Expected)
```bash
curl -X POST http://localhost:8000/interview_round \
  -H "Content-Type: application/json" \
  -d '{"question": "What are your thoughts on AI in healthcare manufacturing specifically?"}'
```
**Expected Result**:
- [ ] `snapshot_type`: "hybrid"
- [ ] `chunks_used`: 0-2
- [ ] `confidence_level`: "medium"
- [ ] `retrieval_quality`: "partial"
- [ ] Note mentions "AI completion"

### Test 3: Full Fallback Snapshot (Expected)
```bash
curl -X POST http://localhost:8000/interview_round \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the capital of France?"}'
```
**Expected Result**:
- [ ] `snapshot_type`: "full_fallback"
- [ ] `chunks_used`: 0
- [ ] `confidence_level`: "low"
- [ ] `retrieval_quality`: "none"
- [ ] `flagged`: true
- [ ] Warning message present

### Test 4: Retrieval Logs
```bash
curl http://localhost:8000/retrieval_logs?limit=5
```
**Expected Result**:
- [ ] Returns array of log entries
- [ ] Each entry has timestamp
- [ ] Each entry shows chunks_retrieved
- [ ] Logs correspond to previous tests

### Test 5: Statistics
```bash
curl http://localhost:8000/snapshot_statistics
```
**Expected Result**:
- [ ] Returns aggregate statistics
- [ ] `total_requests` matches number of tests
- [ ] Rates calculated correctly
- [ ] `zero_chunk_requests` includes fallback tests

---

## 📊 Monitoring Setup

### Daily Checks
- [ ] Review retrieval logs for patterns
- [ ] Check fallback rate (should be <10%)
- [ ] Monitor retrieval times (should be <0.5s)
- [ ] Verify no errors in server logs

### Weekly Checks
- [ ] Analyze snapshot type distribution
- [ ] Review flagged responses
- [ ] Check high-quality retrieval rate (target: >60%)
- [ ] Identify common questions needing more data

### Monthly Checks
- [ ] Audit full retrieval log history
- [ ] Tune thresholds based on performance
- [ ] Plan database expansion
- [ ] Review and update documentation

---

## 🔧 Troubleshooting Guide

### Issue: High Fallback Rate (>20%)
**Symptoms**: Many responses with `snapshot_type: "full_fallback"`
**Causes**:
- [ ] Insufficient interview content
- [ ] Questions outside domain
- [ ] Embedding quality issues
**Solutions**:
- [ ] Add more interview files
- [ ] Improve chunking strategy
- [ ] Review common fallback questions

### Issue: All Hybrid Snapshots (No Interview-Based)
**Symptoms**: No responses with `snapshot_type: "interview_based"`
**Causes**:
- [ ] Threshold too high (`min_score_for_sufficient_insight`)
- [ ] Poor chunk quality
- [ ] Limited interview content
**Solutions**:
- [ ] Lower `min_score_for_sufficient_insight` (try 0.70)
- [ ] Increase `min_chunks_for_interview_based` to 3
- [ ] Improve interview content structure

### Issue: Slow Retrieval (>1s)
**Symptoms**: High `retrieval_time_seconds` in logs
**Causes**:
- [ ] Network latency to Pinecone
- [ ] Large top_k value
- [ ] Pinecone region mismatch
**Solutions**:
- [ ] Check Pinecone region configuration
- [ ] Reduce top_k (try 3)
- [ ] Implement caching for common queries

### Issue: No Chunks Retrieved (Always 0)
**Symptoms**: All responses are fallback
**Causes**:
- [ ] Database not loaded
- [ ] Embedding dimension mismatch
- [ ] Index configuration issue
**Solutions**:
- [ ] Verify data loaded: `curl http://localhost:8000/stats`
- [ ] Check index dimension (should be 768)
- [ ] Recreate index if necessary

---

## 📈 Success Metrics

### Target Performance (Week 1)
- [ ] Retrieval Success Rate: >70%
- [ ] High-Quality Rate: >40%
- [ ] Average Retrieval Time: <1s
- [ ] Fallback Rate: <20%

### Target Performance (Month 1)
- [ ] Retrieval Success Rate: >85%
- [ ] High-Quality Rate: >60%
- [ ] Average Retrieval Time: <0.5s
- [ ] Fallback Rate: <10%

### Target Performance (Steady State)
- [ ] Retrieval Success Rate: >90%
- [ ] High-Quality Rate: >70%
- [ ] Average Retrieval Time: <0.3s
- [ ] Fallback Rate: <5%

---

## 🎯 Go-Live Checklist

### Pre-Launch
- [ ] All tests passing
- [ ] Documentation reviewed
- [ ] API endpoints verified
- [ ] Logging confirmed working
- [ ] Statistics accessible

### Launch
- [ ] Server deployed
- [ ] Health checks passing
- [ ] Monitoring dashboard setup
- [ ] Team trained on system

### Post-Launch (24h)
- [ ] Review first 100 requests
- [ ] Check error logs
- [ ] Verify retrieval distribution
- [ ] Gather initial feedback

### Post-Launch (1 week)
- [ ] Analyze performance metrics
- [ ] Tune thresholds if needed
- [ ] Document common issues
- [ ] Plan database enhancements

---

## 📞 Support Contacts

**System Owner**: Interview Intelligence Team  
**Documentation**: See SNAPSHOT_SYSTEM.md  
**Quick Reference**: See QUICK_REFERENCE.md  
**Architecture**: See ARCHITECTURE.txt  

---

**Checklist Version**: 1.0  
**Last Updated**: January 16, 2026  
**Status**: Ready for Deployment
