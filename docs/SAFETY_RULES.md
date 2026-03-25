# Elevana - Safety Rules & Crisis Protocols

## 1. Overview
Safety is the foundational principle of Elevana. We employ a layered approach to safety that includes hard coded crisis filters, semantic guardrails, and mission-specific agent prompts.

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
3. **Emergency Hotline:**
4. The user is provided with the **Befrienders Kenya** hotline (**0800 723 253**) and the general emergency number (**999**).
**Chiromo Hospital Group** - 0800 220 000
**Kenya Red Cross** - 1199
**Emergency Medicine Kenya Foundation** - 0800 723 253
Niskize - 0900 620 800
Kenya Police - 911/999/112
Domestic/Sexual Violence
HealthCare Assistance Kenya - 1195
Kimbilio Trust - 1193
Gender Violence Recovery Centre - 0800 720 565
Coalition on Violence Against Women - 0800 720 553
Gender Based Violence - 21094 Or Send Help SMS To 1198
Gender Based Violence For Men - 1195 Or 1196
**Psychological Services**
**Nairobi**
KNH (free for U25)
Kamili Mental Health Organisation - 0700 327 701
Amani Counselling Centre - 0722 626 590
NMS - 0110 008 608 / 0110 008 609 (32 clinics round Nairobi)
**Mombasa**
Amani Counselling Centre - 0723 647 768
Chiromo Hospital Group Nyali - 0792 873 125
**Kisumu**
Amani Counselling Centre - 0722 626 590
TINADA Youth Organisation - 0724 018 799
**Eldoret**
Hopewell Counselling - 0717 296 275
**Nakuru**
PDO Kenya - 0774 354 618 (Monthly Support Group)
Jawabu Therapy & Counselling - 0708 065 599
6. **Visibility:** The UI highlights the emergency information with high prominence.
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
