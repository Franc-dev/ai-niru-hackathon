# Task 002: Make the System Work End-to-End.

**Status:** ⚪ Not Started  
**Priority:** High  
**Created:** 2026-02-08  
**Assignee:** TBD

## Focus
Make the system work end-to-end: backend API foundation, agent reasoning (ReAct), chat flow, RAG pipeline, and basic chat frontend.

## Objectives

### 1. Implement Backend API Foundation
- [ ] Ensure chat endpoints are wired and validated (POST /api/v1/chat/, GET /api/v1/chat/history/{conversation_id})
- [ ] Request/response models and error handling
- [ ] Conversation and message persistence (MongoDB)
- [ ] Health and dependency checks ready for agent + RAG

### 2. Build Agent Reasoning Loop (Basic ReAct Flow)
- [ ] Implement ReAct-style loop: Thought → Action → Observation → (repeat or final answer)
- [ ] Integrate with LLM for reasoning steps
- [ ] Support tools/actions (e.g. RAG retrieval, optional external tools)
- [ ] Produce final assistant response from the loop

### 3. Integrate Chat Flow
- [ ] Incoming user message → agent service
- [ ] Safety rule checking in pipeline (per ARCHITECTURE + SAFETY_RULES)
- [ ] Agent uses RAG when needed for grounded answers
- [ ] Store user + assistant messages in conversation history
- [ ] Return assistant response to client

### 4. Set Up RAG Pipeline
- [ ] **Ingestion:** Ingest documents (e.g. from a known path or API), chunk text, generate embeddings, index in vector DB
- [ ] **Retrieval:** Given a query (or current turn), retrieve top-k relevant chunks
- [ ] Choose/configure vector DB (Chroma/Pinecone/Weaviate or existing placeholder)
- [ ] Embedding model selection and configuration
- [ ] RAG pipeline callable by the agent within the reasoning loop

### 5. Basic Frontend for Chat Interaction
- [ ] Chat UI: message list + input
- [ ] Send message → POST /api/v1/chat/ (with conversation_id or new conversation)
- [ ] Display assistant replies and loading state
- [ ] Optional: load conversation history (GET /api/v1/chat/history/{conversation_id})
- [ ] Basic styling and error handling

## Deliverables

- [ ] **Chat-based agent working end-to-end** — User sends a message; backend runs safety check → agent (ReAct) → RAG when needed → stored response → returned to frontend.
- [ ] **RAG returning grounded responses** — Ingested content is retrievable; agent uses retrieved chunks to produce answers grounded in the knowledge base.

## Technical Details

### Backend
- **API:** FastAPI v1 chat + health; Pydantic request/response models.
- **Agent:** `services/agent.py` — ReAct loop with Thought/Action/Observation; optional tool calls (RAG retrieval).
- **RAG:** Ingestion script or endpoint; retrieval function returning chunks; used inside agent as a tool/source.
- **DB:** MongoDB for conversations/messages; vector DB for embeddings and similarity search.

### Frontend
- **Chat:** Single view with message list and input; call `POST /api/v1/chat/` and show response; optional history fetch.
- **Stack:** React, TypeScript, TanStack Query, Axios (per ARCHITECTURE).

### Data Flow (End-to-End)
1. User submits message in frontend.
2. Frontend → `POST /api/v1/chat/` (body: message, conversation_id optional).
3. Backend: validate → safety check → agent.run(message, conversation_id).
4. Agent: ReAct loop; when “search knowledge” action → RAG retrieval → observation → continue or answer.
5. Final answer + optional metadata stored in MongoDB (conversation + messages).
6. Response returned to frontend; UI updates with assistant message.

## Definition of Done

- User can open the app, type a message, and receive an assistant reply.
- Assistant replies can be grounded in RAG (e.g. ask a question about ingested docs and see content-based answer).
- Conversations and messages are persisted and can be fetched by conversation_id.
- Basic ReAct loop is in place and used for each user turn (even if minimal at first).

## Dependencies

- TASK-001 completed (project structure, architecture, safety rules documented, env setup).
- Vector DB choice and credentials (or local Chroma) for RAG.
- Local model endpoints running (chat + embeddings) for agent and RAG.

## Next Steps (Post TASK-002)

- Harden safety rule checking and escalation (implement service from SAFETY_RULES).
- Improve ReAct (more tools, better prompts, streaming).
- Enhance RAG (re-ranking, hybrid search, more sources).
- Staging environment and CI/CD.
- Authentication and rate limiting.

## Notes

- ReAct can start minimal: one “search” action that calls RAG; expand tools later.
- RAG ingestion can be CLI or one-off script; retrieval is the critical path for “grounded responses.”
- Frontend can be a single page with messages + input; polish in later tasks..
