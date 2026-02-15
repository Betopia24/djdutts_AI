# Deterministic Gating Validation

This directory contains validation scripts to test the deterministic gating and EI behavior as requested.

## Quick Setup & Run

### Prerequisites
1. **OpenAI API Key**: You need a valid OpenAI API key
2. **Python 3.8+**: Make sure Python is installed

### Setup Steps

1. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Create Environment File**:
   ```powershell
   copy .env.example .env
   ```
   
3. **Edit .env file** and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your-actual-api-key-here
   ```

### Run Validation

**Quick Demo** (Recommended):
```powershell
python quick_gating_demo.py
```

**Full Validation Suite**:
```powershell
python validate_deterministic_gating.py
```

## Expected Results

### PRIMARY Example
- **Output Class**: `primary`
- **Snapshot Type**: `interview_based`
- **Chunks**: ≥2 chunks from ≥2 different interviews
- **Citations**: Structured metadata with:
  - `interview_id`
  - `executive_name`
  - `chunk_id`
  - `similarity_score`

### FULL_BACKUP/REFUSE Example  
- **Output Class**: `full_backup` or `refused`
- **Snapshot Type**: `full_backup_refusal` or `refused`
- **Chunks**: 0 chunks (no relevant evidence)
- **Response**: Deterministic refusal without authoritative strategy language

## Key Validation Points

✅ **Deterministic Gate Enforcement**: Decision made BEFORE LLM call  
✅ **Authority Boundaries**: PRIMARY requires ≥2 interviews + ≥2 chunks  
✅ **Citation Structure**: Complete metadata for each chunk used  
✅ **Refusal Behavior**: No strategy generation when evidence is insufficient  

## Architecture Notes

- **Gate Decision**: Final, non-upgradeable decision based on rules
- **LLM Scoring**: Optional, post-gate only, cannot override refusal
- **Evidence Pack**: Only passed chunks are used for generation
- **Bounded Insight**: Responses grounded strictly in evidence