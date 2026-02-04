# AI Niru Hackathon

Full-stack application with FastAPI backend and React TypeScript frontend.

## Tech Stack

- **Backend:** FastAPI + MongoDB
- **Frontend:** React + TypeScript + TanStack Query
- **Build Tool:** Vite

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB (local or Atlas)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MongoDB URL
uvicorn main:app --reload
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env if needed
npm run dev
```

Frontend runs on `http://localhost:3000`

## Project Structure

```
ai-niru-hackathon/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── docs/            # Documentation
└── tasks/           # Task tracking
```

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [Safety Rules](./docs/SAFETY_RULES.md)
- [Tasks](./tasks/TASK-001.md)

## Development

See individual task files in `tasks/` directory for current work items.

## License

See LICENSE file.
