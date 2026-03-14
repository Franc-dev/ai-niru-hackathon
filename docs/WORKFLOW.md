# Elevana Mental Health Assistant - Architecture & Workflow

## Overview

Elevana is a bilingual (Swahili/English) mental health chatbot that provides supportive responses based on a curated knowledge base. It uses **Hybrid - Pinecone and chroma - semantic similarity** (not generative AI) to ensure zero hallucinations.

## System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────┐
│   Frontend  │────▶│   Backend   │────▶│  Sklearn+RAG   │────▶│ Pinecone │
│  (React UI) │     │  (FastAPI) │     │   (Server)     │     │  (KB)    │
│ :5173       │     │  :8000     │     │    :8002        │     │          │
└─────────────┘     └─────────────┘     └─────────────────┘     └──────────┘
```

## Technology Stack

| Component | Technology | Port |
|-----------|-----------|------|
| Frontend | React + TypeScript | 5173 |
| Backend | FastAPI (Python) | 8000 |
| ML Server | FastAPI + sklearn + Pinecone | 8002 |
| Database | MongoDB | 27017 |
| Vector DB | Pinecone | Cloud |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | - |

## Step-by-Step Workflow

### Step 1: User Sends Message (Frontend)

**Location:** `frontend/src/App.tsx`

- User types message at `http://localhost:5173`
- Frontend sends POST request to `http://localhost:8000/api/v1/chat`

```typescript
// Example request
POST /api/v1/chat
{
  "messages": [
    {"role": "user", "content": "habari"}
  ]
}
```

### Step 2: Backend Receives Request (FastAPI)

**Location:** `backend/api/v1/endpoints/chat.py`

- Receives the request
- Authenticates user (if required)
- Calls agent service

### Step 3: Agent Service Routes Request

**Location:** `backend/services/agent.py`

- Reads `LOCAL_MODEL_URL` from `.env`
- Forwards request to sklearn+RAG server

```python
# Configuration in .env
LOCAL_MODEL_URL=http://localhost:8002/v1/chat
```

### Step 4: Sklearn+RAG Server Processes (Main Logic)

**Location:** `training/scripts/4_serve_sklearn_rag.py`

#### Step 4a: Language Detection
```python
def detect_language(text: str) -> str
```
- Detects if message is Swahili or English
- Uses keyword matching (hello, how, I, my → English)
- Default: Swahili

#### Step 4b: Crisis Detection (CRITICAL - Checked FIRST)
```python
def detect_crisis(text: str) -> bool
```
- Checks for crisis keywords BEFORE any other processing

**Swahili Keywords:**
- kujiua, kujiharibia, kujidhuru, nataka kufa, siwezi kuishi
- sina sababu ya kuishi, taka kujiua, mwisho wa kuchukua

**English Keywords:**
- suicide, kill myself, want to die, end my life
- hurt myself, self harm, no reason to live, suicidal

**Response:** Returns emergency hotline (0800 723 253 - Befrienders Kenya)

#### Step 4c: Pinecone Similarity Search

If NOT crisis:

1. **Embed the query** using sentence-transformers:
   ```python
   query_embedding = embedder.encode(user_message).tolist()
   ```

2. **Search Pinecone** for similar entries:
   ```python
   results = pinecone_index.query(
       vector=query_embedding,
       top_k=3,
       include_metadata=True
   )
   ```

3. **Check similarity score** (threshold: 0.15)

#### Step 4d: Return Response

- If match found (score >= 0.15): Return Pinecone response
- If no match: Return generic fallback response

### Step 5: Pinecone Knowledge Base

**Data:** 1,660 bilingual Q&A pairs

**Structure:**
```json
{
  "question": "nahisi huzuni",
  "response": "Ninakusikia. Huzuni ni...",

  "language": "sw",
  "category": "depression"
}
```

**Categories covered:**
- greeting, depression, anxiety, stress, loneliness
- relationship, family, sleep, anger, trauma
- grief, addiction, selfharm, suicidal, motivation
- panic, eating, social, health, support

## Response Flow Diagram

```
User Message: "habari"
     │
     ▼
┌─────────────────────────────────┐
│  Language Detection             │
│  Output: 'sw'                  │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Crisis Detection              │
│  Keywords: none found          │
│  Output: is_crisis = False     │
└───────────────┬─────────────────┘
                │
                ▼ (False)
┌─────────────────────────────────┐
│  Pinecone Similarity Search    │
│  Query: "habari"               │
│  Top match: score 0.65         │
│  Response: "Habari! Nina..."    │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Return Response               │
│  Method: pinecone_rag          │
└─────────────────────────────────┘
```

## Configuration Files

### .env
```
LOCAL_MODEL_URL=http://localhost:8002/v1/chat
MONGODB_URL=mongodb://localhost:27017
```

### Server Configuration (4_serve_sklearn_rag.py)
```python
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = "swahili-mental-health"
EMBEDDER = "sentence-transformers/all-MiniLM-L6-v2"
CRISIS_THRESHOLD = 0.15
```

## Start Commands

```bash
# Terminal 1: Sklearn+RAG Server (port 8002)
training_env\Scripts\python.exe training\scripts\4_serve_sklearn_rag.py

# Terminal 2: Backend (port 8000)
uvicorn backend.main:app --reload --port 8000

# Terminal 3: Frontend (port 5173)
cd frontend && npm run dev
```

## Testing

```bash
# Test server directly
training_env\Scripts\python.exe test_sklearn_server.py

# Test Pinecone
training_env\Scripts\python.exe check_pinecone.py
```

## Key Features

1. **Zero Hallucinations** - All responses from curated KB
2. **Bilingual** - Swahili and English fully supported
3. **Crisis Detection** - Immediate hotline for suicide/self-harm
4. **Fast Response** - <500ms (no LLM generation)
5. **Similarity-based** - Uses Pinecone semantic search

## Emergency Resources

- **Befrienders Kenya:** 0800 723 253 (free, 24/7, confidential)
- **Emergency:** 999

---

Last Updated: March 2026
