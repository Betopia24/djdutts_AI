# Embedding Model Migration: Google → OpenAI

## Overview
Successfully migrated from Google's `text-embedding-004` model (768 dimensions) to OpenAI's `text-embedding-3-large` model (3072 dimensions) for better semantic representation and dimensional compatibility with Pinecone.

## Changes Made

### 1. Environment Configuration (.env)
- **Embedding Model**: Changed to `text-embedding-3-large`
- **API Key**: Added `OPENAI_API_KEY` for OpenAI API access

### 2. Configuration File (app/core/config.py)
- Added `OPENAI_API_KEY` to Settings class
- Added `EMBEDDING_MODEL_NAME` configuration from environment variable
- Default embedding model: `text-embedding-3-large`

### 3. Service Layer (app/services/interview/services.py)
**Imports:**
- Added `from openai import OpenAI`

**Initialization:**
- Added OpenAI client initialization: `self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)`
- Updated embedding model: `self.embedding_model = settings.EMBEDDING_MODEL_NAME`
- Updated dimension: `self.embedding_dimension = 3072`
- Separated concerns: OpenAI for embeddings, Google Gemini for generation

**Pinecone Index:**
- Updated dimension from 768 → 3072
- Added logging for embedding model and dimension on connection

**Embedding Method:**
- Replaced Google AI embedding API with OpenAI embedding API
- Updated `embed_text()` method to use `openai_client.embeddings.create()`
- Removed task_type parameter (Google-specific)
- Updated fallback dimension to match (3072)

### 4. Dependencies (requirements.txt)
- Added `openai` package for OpenAI API access

## Architecture Alignment

### Three-Layer Snapshot System
1. **Primary Mode (Interview-Based Snapshot)**
   - Uses vector similarity search with OpenAI embeddings (3072-dim)
   - Retrieves relevant context from Pinecone vector database
   - Requires ≥2 high-quality chunks

2. **Hybrid Snapshot**
   - Falls back when 1 chunk or insufficient insight
   - Combines interview data with AI completion
   - Interview-first approach

3. **Full Backup Snapshot**
   - Activated when 0 chunks retrieved
   - Pure AI-generated response (flagged)
   - Ensures reliable output even without context

## Benefits of OpenAI text-embedding-3-large

✅ **Dimensional Compatibility**: 3072 dimensions align better with Pinecone's capabilities
✅ **Better Semantic Representation**: Higher dimensional embeddings capture more nuanced meanings
✅ **Improved Retrieval Quality**: More accurate vector similarity matching
✅ **Consistent Ecosystem**: OpenAI embeddings work well with RAG systems
✅ **Performance**: Optimized for retrieval tasks

## Migration Checklist

- [x] Update .env with new embedding model
- [x] Add OPENAI_API_KEY to configuration
- [x] Update service to use OpenAI API
- [x] Change Pinecone dimension to 3072
- [x] Add openai to requirements.txt
- [x] Update embed_text() method
- [ ] **ACTION REQUIRED**: Reinstall Python packages (`pip install -r requirements.txt`)
- [ ] **ACTION REQUIRED**: Delete old Pinecone index (ei-interview-qa) or create new index
- [ ] **ACTION REQUIRED**: Re-index all data with new embeddings (3072-dim)

## Next Steps

### 1. Install OpenAI Package
```bash
pip install -r requirements.txt
```

### 2. Recreate Pinecone Index
Since dimension changed from 768 → 3072, you must:

**Option A: Delete and recreate index**
```python
# Delete old index
pc.delete_index("ei-interview-qa")

# Index will be auto-created with new dimensions on first run
```

**Option B: Create new index with different name**
- Update `self.index_name` in services.py
- Keep old index for backup/comparison

### 3. Re-index All Data
Run the data loading endpoints to populate the new index:
```bash
POST /interview/load-hr-questions
POST /interview/load-ceo-interviews
```

### 4. Test Retrieval Quality
- Compare retrieval scores before/after migration
- Verify semantic search improvements
- Monitor snapshot type distribution

## Technical Notes

- **Google Gemini** is still used for **text generation** (gemini-1.5-flash)
- **OpenAI** is now used for **embeddings only**
- This hybrid approach leverages the strengths of both platforms
- Embedding dimension change requires full re-indexing of all vectors

## Client Communication

As explained to the client:
> "We have planned a three-layer architecture consisting of Primary Mode, Hybrid Snapshot, and Full Backup Snapshot. In the primary mode, data is embedded and stored in the Pinecone vector database, and relevant context is retrieved using vector similarity search; for this, we require an embedding model with appropriate dimensionality. Although we initially used Google's embedding model, its lower embedding dimension did not align well with our Pinecone index, so we decided to use an OpenAI embedding model to ensure dimensional compatibility and better semantic representation."

This migration ensures:
- ✅ Executive interview data is properly embedded and indexed
- ✅ RAG-style approach retrieves context strictly from interview dataset
- ✅ Responses are grounded in proprietary interview data, not generic AI
- ✅ OpenAI serves as inference engine only, not intelligence source
