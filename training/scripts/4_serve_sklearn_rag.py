"""
FastAPI server using Pinecone semantic similarity (NO sklearn)

Run:
  python training/scripts/4_serve_sklearn_rag.py
  Server runs on http://localhost:8002
"""
import re
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Configuration
PINECONE_API_KEY = "pcsk_5X3d4w_7dsGKYMHVgosaeTm68hwnxu2NhcyQ6LBSSKZZUaKaGhZWxafjHU2bdw9AMBCAgW"
PINECONE_INDEX = "swahili-mental-health"

# Globals
_pinecone_index = None
_embedder = None

app = FastAPI(title="Pinecone RAG Mental Health API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    max_new_tokens: int = 180
    temperature: float = 0.0
    top_p: float = 1.0
    repetition_penalty: float = 1.08

class ChatResponse(BaseModel):
    content: str
    method: str
    categories: List[str]
    confidence: float
    rag_score: float = 0.0
    crisis_detected: bool = False

# Crisis detection keywords
CRISIS_KEYWORDS_SW = [
    'kujiua', 'kujiharibia', 'kujidhuru', 'nataka kufa', 'siwezi kuishi',
    'mwisho wa kuchukua', 'pema ni kufa', 'siogopi kufa', 'taka kujiua',
    'sina sababu ya kuishi', 'ni mzigo', 'watu wangekuwa bwana'
]

CRISIS_KEYWORDS_EN = [
    'suicide', 'kill myself', 'want to die', 'end my life', 'better off dead',
    'hurt myself', 'self harm', 'self-harm', 'no reason to live', 'suicidal',
    'want to hurt myself', 'better without me', 'everyone would be better'
]

def detect_language(text: str) -> str:
    """Detect if text is Swahili or English"""
    text_lower = text.lower()
    
    # Check for common English words (no spaces needed)
    english_words = [
        'hello', 'hi', 'hey', 'there', 'how', 'what', 'why', 'when',
        'i', 'my', 'me', 'the', 'and', 'is', 'are', 'feel', 'feeling',
        'want', 'need', 'help', 'have', 'been', 'you', 'your', 'can',
        'would', 'could', 'should', 'will', 'do', 'does', 'did', 'sorry',
        'thank', 'thanks', 'please', 'good', 'bad', 'sad', 'happy',
        'anxious', 'depressed', 'anxiety', 'depression', 'stress', 'work',
        'life', 'love', 'family', 'friend', 'friends', 'alone', 'lonely'
    ]
    
    # Check for Swahili characters (not in English)
    swahili_chars = set('bcdfghjklmnpqrstvwxyz')
    has_swahili = any(c in swahili_chars for c in text_lower.replace(' ', ''))
    
    # Count English word matches
    english_count = sum(1 for word in english_words if word in text_lower)
    
    # If many English words found, it's English
    if english_count >= 1:
        return 'en'
    # If text has typical English structure but no English words, default to English
    elif text_lower.replace(' ', '').isalpha() and not any(c in 'ąęóźńśż' for c in text_lower):
        return 'en'
    else:
        return 'sw'

def detect_crisis(text: str) -> bool:
    """Detect crisis keywords"""
    text_lower = text.lower()
    for keyword in CRISIS_KEYWORDS_SW + CRISIS_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            return True
    return False

def get_crisis_response(language: str) -> str:
    """Emergency response for crisis cases"""
    if language == 'sw':
        return """MSAIDA WA HARAKA!

Ninakusikia na nina wasiwasi mkubwa kuhusu usalama wako.

HATUA ZA SASA:
1. Piga simu SASA: 0800 723 253 (Befrienders Kenya)
   - Bure kabisa
   - Siri 100%
   - Wanasaidia 24/7

2. Ikiwa uko kwenye hatari ya kujidhuru SASA, piga 999 au nenda hospitali ya karibu

3. Piga simu mtu unayemwamini - rafiki, familia, au jirani

Je, uko salama kwa sasa? Kuna mtu anayeweza kukaa nawe?

Maisha yako yana thamani. Tafadhali pata msaada SASA."""
    else:
        return """URGENT HELP NEEDED!

I hear you and I'm deeply concerned about your safety.

IMMEDIATE STEPS:
1. Call NOW: 0800 723 253 (Befrienders Kenya)
   - Completely free
   - 100% confidential
   - Available 24/7

2. If you're in immediate danger, call 999 or go to nearest hospital

3. Call someone you trust - friend, family, or neighbor

Are you safe right now? Is there someone who can stay with you?

Your life has value. Please get help NOW."""

def get_generic_response(language: str) -> str:
    """Generic fallback response"""
    if language == 'sw':
        return """Ninakusikiliza. Mimi ni msaidizi wa afya ya akili.

Ninaweza kukusaidia na:
- Huzuni na wasiwasi
- Matatizo ya familia au mahusiano
- Msongo wa kazi
- Shida za kulala
- Upweke
- Mabadiliko ya hisia

Je, kuna jambo la afya ya akili au ustawi wa kihemko ungependa kuzungumzia?

Au piga 0800 723 253 (Befrienders Kenya) - bure na siri."""
    else:
        return """I'm listening. I'm a mental health support assistant.

I can help you with:
- Depression and anxiety
- Family or relationship issues
- Work stress
- Sleep problems
- Loneliness
- Emotional wellbeing

Is there something related to mental health or emotional wellbeing you'd like to talk about?

Or call 0800 723 253 (Befrienders Kenya) - free and confidential."""

@app.on_event("startup")
async def load_models():
    """Load Pinecone and sentence transformer"""
    global _pinecone_index, _embedder
    
    print("\n" + "="*60)
    print("LOADING PINEOCNE RAG SERVER")
    print("="*60 + "\n")
    
    print("Connecting to Pinecone...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    _pinecone_index = pc.Index(PINECONE_INDEX)
    print(f"   Connected to '{PINECONE_INDEX}'")
    
    print("Loading embedding model...")
    _embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print("   Embedder loaded")
    
    print("\n" + "="*60)
    print("SERVER READY!")
    print("="*60)
    print("Endpoint: http://localhost:8002/v1/chat")
    print("\n")

@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - Pinecone similarity only"""
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        user_message = request.messages[-1].content.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Empty message")
        
        # 1. Detect language
        language = detect_language(user_message)
        
        # 2. Check for crisis FIRST
        if detect_crisis(user_message):
            return ChatResponse(
                content=get_crisis_response(language),
                method='crisis',
                categories=['crisis'],
                confidence=1.0,
                crisis_detected=True
            )
        
        # 3. Pinecone similarity search
        query_embedding = _embedder.encode(user_message).tolist()
        
        results = _pinecone_index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True
        )
        
        # Check if we have good matches (lowered threshold for small KB)
        if results.matches and results.matches[0].score >= 0.15:
            best_match = results.matches[0]
            response = best_match.metadata.get('response', '')
            question = best_match.metadata.get('question', '')
            category = best_match.metadata.get('category', 'general')
            score = best_match.score
            
            # Get category from metadata
            categories = [category] if category else []
            
            return ChatResponse(
                content=response,
                method='pinecone_rag',
                categories=categories,
                confidence=float(score),
                rag_score=float(score),
                crisis_detected=False
            )
        
        # 4. No good match - return generic
        return ChatResponse(
            content=get_generic_response(language),
            method='generic_fallback',
            categories=[],
            confidence=0.0,
            crisis_detected=False
        )
    
    except Exception as e:
        print(f"ERROR in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "pinecone_connected": _pinecone_index is not None,
        "embedder_loaded": _embedder is not None
    }

if __name__ == "__main__":
    import uvicorn
    
    print("\nStarting Pinecone RAG Server on http://localhost:8002")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
