# Setup Guide

Quick setup instructions for getting the project running locally.

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- MongoDB (local installation or MongoDB Atlas account)

## Backend Setup

1. **Navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
   - Windows (CMD): `venv\Scripts\activate.bat`
   - macOS/Linux: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your MongoDB URL:
   ```
   MONGODB_URL=mongodb://localhost:27017
   ```

6. **Run the server**
   ```bash
   python run.py
   ```
   Or:
   ```bash
   uvicorn main:app --reload
   ```

   Server will be available at `http://localhost:8000`
   API docs at `http://localhost:8000/docs`

## Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment (optional)**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` if your backend runs on a different port:
   ```
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

4. **Run development server**
   ```bash
   npm run dev
   ```

   Frontend will be available at `http://localhost:3000`

## MongoDB Setup

### Option 1: Local MongoDB

1. Install MongoDB locally
2. Start MongoDB service
3. Use connection string: `mongodb://localhost:27017`

### Option 2: MongoDB Atlas (Cloud)

1. Create account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster
3. Get connection string
4. Update `.env` with your Atlas connection string

## Verify Installation

1. **Backend Health Check**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "healthy"}`

2. **API Health Check**
   ```bash
   curl http://localhost:8000/api/v1/health/
   ```
   Should return: `{"status": "ok", "service": "api"}`

3. **Frontend**
   - Open `http://localhost:3000` in browser
   - Should see "AI Niru Hackathon" page

## Troubleshooting

### Backend Issues

- **Import errors**: Make sure you're in the backend directory and virtual environment is activated
- **MongoDB connection errors**: Verify MongoDB is running and connection string is correct
- **Port already in use**: Change port in `run.py` or kill process using port 8000

### Frontend Issues

- **Module not found**: Run `npm install` again
- **API connection errors**: Check that backend is running and CORS is configured
- **Port already in use**: Change port in `vite.config.ts`

## Next Steps

- Review [Architecture Documentation](./docs/ARCHITECTURE.md)
- Check [Task 001](./tasks/TASK-001.md) for current work
- Read [Safety Rules](./docs/SAFETY_RULES.md)
