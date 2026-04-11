# 1v1 RAG Quiz System

Real-time multiplayer quiz platform with AI-powered question generation using Retrieval-Augmented Generation (RAG).

## Features

- ✅ **Real-time 1v1 quiz battles** - Compete against friends or random players
- ✅ **Guest mode** - Play instantly without signup
- ✅ **AI-powered Document RAG** - Upload a PDF for personalized AI-generated questions
- ✅ **Competition & Spectator Modes** - Host large sessions with leaderboard tracking
- ✅ **Automatic cleanup** - Questions and data deleted after game ends
- ✅ **Speed-based scoring** - Faster answers earn more points
- ✅ **Server-authoritative gameplay** - No cheating possible

## Tech Stack

**Frontend:** React 18 + Vite  
**Backend:** Python FastAPI + WebSocket  
**AI Service:** Python FastAPI + RAG (sentence-transformers + FAISS)  
**Database:** MongoDB  
**LLM:** Google Gemini 1.5/2.0

---

## 🚀 Quick Start (Local Setup)

### Prerequisites

- Node.js 16+
- Python 3.9+ 
- MongoDB (Running locally or via Atlas)

### 1. Clone & Install
```bash
# Clone repository
git clone https://github.com/yourusername/1v1-rag-quiz.git
cd 1v1-rag-quiz

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install AI service dependencies
cd ai-service
pip install -r requirements.txt

# Install frontend dependencies
cd ../../frontend
npm install
```

### 2. Environment Setup

*Important: Do not commit your `.env` files to GitHub.*

**Backend (`backend/.env`):**
```env
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=quiz_battle
SECRET_KEY=your-super-secret-key-change-this-in-production
AI_SERVICE_URL=http://localhost:8001
```

**AI Service (`backend/ai-service/.env`):**
```env
GOOGLE_API_KEY=your-google-gemini-api-key-here
```

### 3. Start Development Servers
You will need to open **3 separate terminal windows**:

**Terminal 1 - Backend API:**
```bash
cd backend
python main.py
# Runs on http://localhost:8000
```

**Terminal 2 - AI RAG Service:**
```bash
cd backend/ai-service
python main.py
# Runs on http://localhost:8001
```

**Terminal 3 - Frontend UI:**
```bash
cd frontend
npm run dev
# Runs on http://localhost:5173
```

---

## 🔒 GitHub Deployability Checks

This project is configured securely for GitHub. 
- All `.env` environment files are correctly ignored by `.gitignore`.
- No sensitive keys are hard-coded into the repository.
- File uploads (`uploads/`), local dependencies (`node_modules/`), and python binaries (`__pycache__`) are safely ignored.

To upload this as a single unified repository to GitHub:
1. Ensure there are no nested `.git` folders in `/backend` or `/frontend`.
2. Run `git init` at the root of `1v1-rag-quiz`.
3. Add and commit your changes (`git add . && git commit -m "Initial commit"`).
4. Push to your GitHub repository.