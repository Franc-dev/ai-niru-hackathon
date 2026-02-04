# Architecture Documentation

## Overview

AI Niru Hackathon - A full-stack application with FastAPI backend and React TypeScript frontend.

## Tech Stack

### Backend
- **Framework:** FastAPI
- **Database:** MongoDB (via Motor async driver)
- **Vector DB:** TBD (Pinecone/Weaviate/Chroma placeholder)
- **Language:** Python 3.11+

### Frontend
- **Framework:** React 18
- **Language:** TypeScript
- **Query Library:** TanStack Query (React Query)
- **Build Tool:** Vite
- **HTTP Client:** Axios

## Architecture Decisions

### API Design
- RESTful API with versioning (`/api/v1/`)
- JSON request/response format
- Async/await pattern throughout

### Database
- MongoDB for primary data storage
- Vector database for embeddings and semantic search (to be selected)
- Connection pooling via Motor

### Agent Flow
- **Status:** To be finalized
- **Components:**
  - Message processing
  - Safety rule checking
  - Response generation
  - Escalation handling

### Voice + Chat
- **Status:** To be finalized
- **Approach:** TBD
- **Integration:** TBD

## Project Structure

```
ai-niru-hackathon/
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── core/               # Core configuration
│   │   ├── config.py       # Settings management
│   │   └── database.py     # MongoDB connection
│   ├── api/                # API routes
│   │   └── v1/            # API version 1
│   │       ├── router.py  # Main router
│   │       └── endpoints/ # Endpoint handlers
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   │   ├── agent.py       # Agent service
│   │   └── vector_db.py   # Vector DB service
│   └── requirements.txt   # Python dependencies
│
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/          # API client & queries
│   │   ├── components/   # React components
│   │   ├── App.tsx       # Main app
│   │   └── main.tsx      # Entry point
│   ├── package.json      # Node dependencies
│   └── vite.config.ts    # Vite config
│
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md   # This file
│   └── SAFETY_RULES.md   # Safety rules
│
└── tasks/                 # Task tracking
    └── TASK-001.md       # First task
```

## API Endpoints

### Health
- `GET /api/v1/health/` - Health check

### Chat
- `POST /api/v1/chat/` - Send chat message
- `GET /api/v1/chat/history/{conversation_id}` - Get chat history

## Data Flow

1. **Frontend** → User interaction
2. **TanStack Query** → API call via Axios
3. **FastAPI** → Request handling
4. **Agent Service** → Message processing
5. **Safety Rules** → Content checking
6. **Vector DB** → Semantic search (if needed)
7. **MongoDB** → Store conversation
8. **Response** → Back to frontend

## Environment Configuration

### Backend (.env)
- `MONGODB_URL` - MongoDB connection string
- `MONGODB_DB_NAME` - Database name
- `VECTOR_DB_TYPE` - Vector DB provider
- `VECTOR_DB_URL` - Vector DB URL
- `VECTOR_DB_API_KEY` - Vector DB API key
- `ENVIRONMENT` - dev/staging/prod
- `DEBUG` - Debug mode

### Frontend (.env)
- `VITE_API_BASE_URL` - Backend API URL

## Development Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Deployment Considerations

- **Backend:** Uvicorn/Gunicorn with ASGI
- **Frontend:** Static build via Vite
- **Database:** MongoDB Atlas or self-hosted
- **Vector DB:** Cloud provider (Pinecone/Weaviate)

## Security Considerations

- CORS configuration
- Input validation via Pydantic
- Safety rule enforcement
- Escalation flow for unsafe content
- API authentication (to be implemented)

## Future Enhancements

- [ ] Authentication & Authorization
- [ ] WebSocket support for real-time chat
- [ ] Voice input/output integration
- [ ] Advanced agent flow with RAG
- [ ] Monitoring and logging
- [ ] Rate limiting
- [ ] Caching layer
