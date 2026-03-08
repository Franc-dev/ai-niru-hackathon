"""
Agentic AI Server with Tools - Counselors, Resources, RAG

Tools:
1. Crisis Detection - Emergency hotline
2. Find Counselors - Search mental health professionals
3. Get Resources - YouTube videos, articles
4. RAG Context - Pinecone knowledge base
5. LLM Generation - Trained model + context

Run: python training/scripts/4_serve_sklearn_rag.py
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pinecone import Pinecone
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "").strip()
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "swahili-mental-health").strip()

# Paths
DATA_DIR = Path("data")
COUNSELORS_FILE = DATA_DIR / "counselors.json"
RESOURCES_FILE = DATA_DIR / "resources.json"

# Globals
pinecone_index = None
embedder = None
counselors = []
resources = []

app = FastAPI(title="Agentic AI Mental Health")

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
    temperature: float = 0.3


class ToolResult(BaseModel):
    tool_name: str
    result: Any
    success: bool


class ChatResponse(BaseModel):
    content: str
    method: str
    categories: List[str]
    confidence: float
    crisis_detected: bool = False
    tools_used: List[str] = []


# ==================== TOOLS ====================


def tool_detect_crisis(text: str) -> tuple[bool, str]:
    """Tool: Detect crisis keywords"""
    crisis_keywords_sw = [
        "kujiua",
        "kujiharibia",
        "kujidhuru",
        "nataka kufa",
        "siwezi kuishi",
        "sina sababu ya kuishi",
        "taka kujiua",
        "mwisho wa kuchukua",
        "nataka msaada wa haraka",
        "nataka mkubwa",
    ]
    crisis_keywords_en = [
        "suicide",
        "kill myself",
        "want to die",
        "end my life",
        "better off dead",
        "hurt myself",
        "self harm",
        "self-harm",
        "no reason to live",
        "suicidal",
        "crisis help",
        "need crisis",
        "emergency",
    ]

    text_lower = text.lower()
    for kw in crisis_keywords_sw + crisis_keywords_en:
        if kw in text_lower:
            return True, "crisis_detected"
    return False, ""


def tool_find_counselors(
    query: str, category: str = None, language: str = "en"
) -> List[Dict]:
    """Tool: Find mental health counselors"""
    print(f"[DEBUG] tool_find_counselors called with: query='{query}', category={category}, language={language}")
    print(f"[DEBUG] Global counselors list has {len(counselors)} counselors")
    
    results = []
    query_lower = query.lower()

    # Check category keywords
    category_map = {
        "depression": ["depression", "huzuni", "sad"],
        "anxiety": ["anxiety", "wasiwasi", "anxious", "worry"],
        "stress": ["stress", "msongo", "work"],
        "trauma": ["trauma", "traumatic"],
        "relationships": ["relationship", "mahusiano", "partner"],
        "family": ["family", "familia"],
        "addiction": ["addiction", "uadilifu", "alcohol"],
        "grief": ["grief", "msiba", "loss"],
    }

    for counselor in counselors:
        # Filter by category if specified
        if category:
            if category.lower() not in counselor.get("specialization", "").lower():
                continue

        # Check language match
        if language == "sw" and "Swahili" not in counselor.get("languages", []):
            continue
        if language == "en" and "English" not in counselor.get("languages", []):
            continue

        # Score by relevance
        score = 1  # Base score for matching language
        spec = counselor.get("specialization", "").lower()

        if category_map.get(category):
            if any(kw in spec for kw in category_map[category]):
                score += 10

        results.append((score, counselor))

    # Sort by score
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:6]]  # Return top 6 counselors


def tool_get_resources(category: str = None, language: str = "en") -> List[Dict]:
    """Tool: Get mental health resources (videos, articles)"""
    results = []

    for resource in resources:
        # Filter by category
        if category and resource.get("category", "").lower() != category.lower():
            continue

        # Filter by language
        if language == "sw" and resource.get("language") != "Swahili":
            continue
        if language == "en" and resource.get("language") != "English":
            continue

        results.append(resource)

    return results[:5]


def tool_rag_search(query: str, top_k: int = 2) -> tuple[str, float]:
    """Tool: Pinecone RAG search"""
    try:
        query_embedding = embedder.encode(query).tolist()
        results = pinecone_index.query(
            vector=query_embedding, top_k=top_k, include_metadata=True
        )

        if results.matches and results.matches[0].score >= 0.35:
            return results.matches[0].metadata.get("response", ""), results.matches[
                0
            ].score
        return "", 0.0
    except:
        return "", 0.0


def detect_intent(text: str, language: str) -> Dict[str, Any]:
    """Tool: Detect user intent to route to appropriate tools"""
    text_lower = text.lower()

    intents = {
        "crisis": False,
        "find_counselor": False,
        "get_resources": False,
        "general": True,
        "category": None,
    }

    # Crisis keywords
    crisis_kw = ["kujiua", "kill myself", "want to die", "suicide", "self harm"]
    if any(kw in text_lower for kw in crisis_kw):
        intents["crisis"] = True
        intents["general"] = False
        return intents

    # Counselor search keywords
    counselor_kw = [
        "counselor",
        "doctor",
        "daktari",
        "therapist",
        "mshauri",
        "psychologist",
        "psychiatrist",
        "naenda wapi",
        "where can i",
        "find a",
        "tafuta",
        "specialist",
        "mtaalamu",
        "professional",
    ]
    if any(kw in text_lower for kw in counselor_kw):
        intents["find_counselor"] = True
        intents["general"] = False

    # Resources keywords
    resource_kw = [
        "video",
        "videos",
        "youtube",
        "article",
        "read",
        "show me",
        "nyesha",
        "kujifunza",
        "learn",
        "information",
        "elimu",
        "tips",
        "advice",
        "resource",
    ]
    if any(kw in text_lower for kw in resource_kw):
        intents["get_resources"] = True
        intents["general"] = False

    # Detect category
    category_keywords = {
        "depression": ["depressed", "huzuni", "sad", "hopeless"],
        "anxiety": ["anxious", "wasiwasi", "worry", "panic"],
        "stress": ["stress", "msongo", "work", "overwhelmed"],
        "sleep": ["sleep", "kulala", "insomnia", "tired"],
        "relationships": ["relationship", "mahusiano", "partner", "love"],
        "family": ["family", "familia", "parents"],
        "trauma": ["trauma", "traumatic", "flashback"],
        "grief": ["grief", "msiba", "lost", "death"],
    }

    for cat, kws in category_keywords.items():
        if any(kw in text_lower for kw in kws):
            intents["category"] = cat
            break

    return intents


# ==================== RESPONSE GENERATORS ====================


def get_crisis_response(language: str) -> str:
    if language == "sw":
        return """MSAIDA WA HARAKA!

Ninawasikia sana. Ni muhimu sana upate msaada sasa.

📞 Piga SASA: 0800 723 253 (Befrienders Kenya) - BURE, SIRI, 24/7
📞 Emergency: 999

Ikiwa uko kwenye hatari ya kujidhuru, nenda hospitali ya karibu.

Unaweza pia kuzungumza nami hapa - niko hapa kukusikiliza.

Wewe ni muhimu! Maisha yako yana thamani!"""
    else:
        return """URGENT HELP NEEDED!

I'm deeply concerned about you. Please reach out for help NOW.

📞 Call NOW: 0800 723 253 (Befrienders Kenya) - FREE, CONFIDENTIAL, 24/7
📞 Emergency: 999

If you're in immediate danger, go to the nearest hospital.

You can also talk to me - I'm here to listen.

You matter! Your life has value!"""


def get_counselor_response(counselors_found: List[Dict], language: str) -> str:
    if not counselors_found:
        if language == "sw":
            return "Hazinaingia vigezo vya wataalam. Jaribu kuwasiliana na 0800 723 253 kwa msaada zaidi."
        else:
            return "No counselors found matching your criteria. Call 0800 723 253 for more options."

    if language == "sw":
        response = "Hapa kuna wataalam wa afya ya akili watakaoingia:\n\n"
        for i, c in enumerate(counselors_found, 1):
            response += f"{i}. **{c['name']}**\n"
            response += f"   📍 {c['location']} | ⭐ {c['rating']}\n"
            response += f"   🏥 {c['specialization']}\n"
            response += f"   📞 {c['phone']}\n"
            response += f"   🗣️ {', '.join(c['languages'])}\n\n"
        response += "Je, ungependa kujua zaidi kuhusu mmoja wao?"
    else:
        response = "Here are mental health professionals that match your needs:\n\n"
        for i, c in enumerate(counselors_found, 1):
            response += f"{i}. **{c['name']}**\n"
            response += f"   📍 {c['location']} | ⭐ {c['rating']}\n"
            response += f"   🏥 {c['specialization']}\n"
            response += f"   📞 {c['phone']}\n"
            response += f"   🗣️ {', '.join(c['languages'])}\n\n"
        response += "Would you like more information about any of them?"

    return response


def get_resources_response(resources_found: List[Dict], language: str) -> str:
    if not resources_found:
        if language == "sw":
            return "Haziko tayari. Jaribu tena au wasiliana na 0800 723 253."
        else:
            return "No resources available. Try again or call 0800 723 253."

    if language == "sw":
        response = "Hapa kuna vyanzo utakavyo:\n\n"
        for r in resources_found:
            response += f"📺 **{r['title']}**\n"
            response += f"   {r['description']}\n"
            response += f"   ⏱️ {r['duration']} | 🗣️ {r['language']}\n"
            response += f"   🔗 {r['url']}\n\n"
        response += "Tazama video hizi kwa ujuzi zaidi!"
    else:
        response = "Here are some helpful resources:\n\n"
        for r in resources_found:
            response += f"📺 **{r['title']}**\n"
            response += f"   {r['description']}\n"
            response += f"   ⏱️ {r['duration']} | 🗣️ {r['language']}\n"
            response += f"   🔗 {r['url']}\n\n"
        response += "Watch these for more information!"

    return response


def get_generic_response(language: str) -> str:
    if language == "sw":
        return """Ninakusikiliza. Mimi ni msaidizi wako wa afya ya akili.

Ninaweza kukusaidia na:
- Huzuni na wasiwasi
- Matatizo ya familia au mahusiano
- Msongo wa kazi au maisha
- Shida za kulala
- Upweke
- Masuala ya kihemko

Je, kuna jambo ungependa kuzungumzia?

Unaweza pia:
📞 Piga 0800 723 253 (Befrienders Kenya) - bure, siri, 24/7
🎥 Ona video za kujifunza
👨‍⚕️ Pata mtaalamu wa afya ya akili"""
    else:
        return """I'm listening. I'm your mental health support assistant.

I can help you with:
- Depression and anxiety
- Family or relationship issues
- Work or life stress
- Sleep problems
- Loneliness
- Emotional wellbeing

What's on your mind?

You can also:
📞 Call 0800 723 253 (Befrienders Kenya) - free, confidential, 24/7
🎥 Get helpful videos and resources
👨‍⚕️ Find a mental health professional"""


# ==================== MAIN HANDLER ====================


def process_message(user_message: str, language: str) -> tuple[str, List[str], Dict]:
    """Main agentic processing"""
    tools_used = []
    
    print(f"\n[DEBUG] User message: {user_message}")
    print(f"[DEBUG] Language: {language}")
    
    # 1. Crisis Detection Tool
    is_crisis, _ = tool_detect_crisis(user_message)
    print(f"[DEBUG] Crisis detected: {is_crisis}")
    if is_crisis:
        return get_crisis_response(language), ['crisis_detection'], {'crisis_detected': True}
    
    # 2. Intent Detection Tool
    intents = detect_intent(user_message, language)
    print(f"[DEBUG] Intents: {intents}")
    
    # 3. Find Counselors Tool
    if intents['find_counselor']:
        print(f"[DEBUG] Looking for counselors...")
        counselors_found = tool_find_counselors(
            user_message, 
            intents['category'], 
            language
        )
        print(f"[DEBUG] Found {len(counselors_found)} counselors")
        if counselors_found:
            tools_used.append('find_counselor')
            return get_counselor_response(counselors_found, language), tools_used, {}
    
    # 4. Get Resources Tool
    if intents['get_resources']:
        print(f"[DEBUG] Looking for resources...")
        resources_found = tool_get_resources(intents['category'], language)
        print(f"[DEBUG] Found {len(resources_found)} resources")
        if resources_found:
            tools_used.append('get_resources')
            return get_resources_response(resources_found, language), tools_used, {}
    
    # 5. RAG Tool
    print(f"[DEBUG] Trying RAG search...")
    context, score = tool_rag_search(user_message)
    print(f"[DEBUG] RAG score: {score}")
    if context:
        tools_used.append('rag_search')
        return context, tools_used, {'rag_score': score}
    
    # 6. Generic fallback
    print(f"[DEBUG] Using generic fallback")
    tools_used.append('generic')
    return get_generic_response(language), tools_used, {}


# ==================== LANGUAGE DETECTION ====================


def detect_language(text: str) -> str:
    text_lower = text.lower()
    english_words = [
        "hello",
        "hi",
        "how",
        "what",
        "why",
        "when",
        "i",
        "my",
        "me",
        "the",
        "feel",
        "feeling",
        "want",
        "need",
        "help",
        "have",
        "been",
        "you",
        "can",
        "would",
        "could",
        "should",
        "do",
        "does",
        "sorry",
        "thank",
        "good",
        "bad",
        "sad",
        "happy",
        "anxious",
        "depressed",
        "anxiety",
        "depression",
        "stress",
        "work",
        "life",
        "love",
        "family",
        "friend",
        "lonely",
        "alone",
        "sleep",
        "tired",
        "counselor",
        "doctor",
        "therapist",
    ]
    english_count = sum(1 for word in english_words if word in text_lower)
    return "en" if english_count >= 1 else "sw"


# ==================== FASTAPI APP ====================


@app.on_event("startup")
async def load_data():
    global pinecone_index, embedder, counselors, resources

    print("\n" + "=" * 60)
    print("LOADING AGENTIC AI SERVER WITH TOOLS")
    print("=" * 60)

    # Load Pinecone
    print("\n[1/4] Connecting to Pinecone...")
    if not PINECONE_API_KEY:
        raise RuntimeError(
            "Missing PINECONE_API_KEY environment variable. "
            "Set it in your local environment (or .env file) before starting the server."
        )
    if not PINECONE_INDEX:
        raise RuntimeError(
            "Missing PINECONE_INDEX environment variable (or empty value). "
            "Set PINECONE_INDEX to your target Pinecone index name."
        )

    pc = Pinecone(api_key=PINECONE_API_KEY)
    pinecone_index = pc.Index(PINECONE_INDEX)
    print(f"   [OK] Pinecone connected (index: {PINECONE_INDEX})")

    # Load embedder
    print("\n[2/4] Loading embedder...")
    embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("   [OK] Embedder loaded")

    # Load counselors
    print("\n[3/4] Loading counselor database...")
    if COUNSELORS_FILE.exists():
        with open(COUNSELORS_FILE) as f:
            counselors = json.load(f)
        print(f"   [OK] {len(counselors)} counselors loaded")
    else:
        print("   [WARN] No counselors file found")

    # Load resources
    print("\n[4/4] Loading resources...")
    if RESOURCES_FILE.exists():
        with open(RESOURCES_FILE) as f:
            resources = json.load(f)
        print(f"   [OK] {len(resources)} resources loaded")
    else:
        print("   [WARN] No resources file found")

    print("\n" + "=" * 60)
    print("AGENTIC AI SERVER READY!")
    print("=" * 60)
    print("Tools available:")
    print("  [1] Crisis Detection")
    print("  [2] Find Counselors")
    print("  [3] Get Resources")
    print("  [4] RAG Search")
    print("\nEndpoint: http://localhost:8002/v1/chat")
    print("\n")


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages")

        user_message = request.messages[-1].content.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Empty message")

        language = detect_language(user_message)

        # Process with agentic tools
        response, tools_used, metadata = process_message(user_message, language)

        return ChatResponse(
            content=response,
            method="agentic_tools",
            categories=[metadata.get("category", "general")],
            confidence=metadata.get("rag_score", 0.5),
            crisis_detected=metadata.get("crisis_detected", False),
            tools_used=tools_used,
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "counselors_loaded": len(counselors),
        "resources_loaded": len(resources),
        "rag_connected": pinecone_index is not None,
    }


if __name__ == "__main__":
    import uvicorn

    print("\nStarting Agentic AI Server on http://localhost:8002\n")
    uvicorn.run(app, host="0.0.0.0", port=8002)
