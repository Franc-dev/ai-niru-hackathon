# Elevana - Safety Rules & Crisis Protocols

## 1. Overview
Safety is the foundational principle of Elevana. We employ a layered approach to safety that includes hardcoded crisis filters, semantic guardrails, and mission-specific agent prompts.

## 2. Crisis Detection Protocol (High Priority)
The Crisis Detection Tool (`4_serve_sklearn_rag.py`) is the most critical safety layer. It is executed **first** for every incoming chat message.

### 2.1 Monitored Keywords (Swahili & English)
The system checks for over 20 specific terms related to self-harm, suicide, and emergency distress, including:
- **Swahili:** kujiua, kujiharibia, kujidhuru, nataka kufa, siwezi kuishi.
- **English:** suicide, kill myself, want to die, end my life, self-harm.

### 2.2 Crisis Response Workflow
When a crisis keyword is detected:
1. **Immediate Interruption:** All other tool logic and agent reasoning are halted.
2. **Canned Response:** A culturally appropriate, empathetic response is returned immediately.
3. **Emergency Hotline:** The user is provided with the **Befrienders Kenya** hotline (**0800 723 253**) and the general emergency number (**999**).
4. **Visibility:** The UI highlights the emergency information with high prominence.

---

## 3. Semantic Guardrails (Off-Topic Filter)
The Guardrails service (`backend/services/guardrails.py`) prevents the model from being misused for non-mental health purposes.

### 3.1 Monitored Topics
The system automatically identifies and redirects users who try to use Elevana for:
- Programming/Coding (Python, Java, Javascript).
- Math, Physics, or Homework help.
- General web search topics (Weather, Stock prices, Cooking recipes).

### 3.2 Redirect Strategy
Instead of a generic error, the system provides a polite redirect in the user's detected language (Swahili/English), explaining that its purpose is mental health and emotional well-being, and inviting the user to share their feelings.

---

## 4. Agent-Level Safety (Voice Agent)
The Voice Agent (`voice_agent.py`) uses **Claude 4.5 Haiku** with a highly specialized system prompt that enforces:
- **Empathetic Neutrality:** Staying present and caring without making medical diagnoses.
- **Short Responses:** Preventing overwhelmed users from receiving long, complex paragraphs.
- **No Formatting:** Ensuring the text-to-speech output is natural and easy to follow.

---

## 5. Implementation Status

| Feature | Implementation Method | Status |
|---------|-----------------------|--------|
| Crisis Keywords | Regex / Pattern Matching | **Operational** |
| Off-Topic Guardrails | Compiled Regex (`guardrails.py`) | **Operational** |
| RAG Confidence Gate | Similarity Threshold (0.35) | **Operational** |
| Human Counselor Linking | Counselor Search Tool | **Operational** |
| Resource Filtering | Resource Search Tool | **Operational** |

---

## 6. Escalation Flow (Internal Logic)

```
User Message
    │
    ▼
┌─────────────────────────────────┐
│ [LAYER 1] Crisis Tool           │──▶ [DETECTED] ──▶ Show Emergency Hotline
└─────────────────────────────────┘
    │
    ▼ [NOT DETECTED]
┌─────────────────────────────────┐
│ [LAYER 2] Guardrails Service    │──▶ [OFF-TOPIC] ──▶ Show Support Redirect
└─────────────────────────────────┘
    │
    ▼ [ON-TOPIC]
┌─────────────────────────────────┐
│ [LAYER 3] Agent Reasoning       │──▶ [PROCESS] ──▶ Provide Empathetic Help
└─────────────────────────────────┘
```

---
*Last Updated: March 2026*
