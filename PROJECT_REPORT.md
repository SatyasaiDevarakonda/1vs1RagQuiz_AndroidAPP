# 1v1 RAG Quiz: Professional Project Report

## Executive Summary
The **1v1 RAG Quiz** system is a real-time, multiplayer educational evaluation platform. It leverages **Retrieval-Augmented Generation (RAG)** to dynamically generate high-quality quiz questions from user-uploaded PDFs, DOCX, or text documents. By combining real-time competitive elements (1v1 matches and competition rooms) with personalized content generation, it provides an engaging and effective learning experience.

---

## 1. Technical Architecture

### 1.1 Frontend (React 18 + Vite)
- **State Management**: React Context API for Authentication and Game state.
- **Communication Layer**: Custom WebSocket service for real-time multiplayer synchronization.
- **Styling**: Vanilla CSS for premium, high-performance UI components.

### 1.2 Backend API (FastAPI)
- **Role**: Serves as the central orchestrator for game logic, room management, and user authentication.
- **WebSocket Manager**: Handles server-authoritative game loops, scoring, and real-time broadcasting.
- **Security**: JWT-based authentication supporting both registered accounts and instant Guest Mode sessions.
- **Database**: MongoDB for persistent storage of user profiles, game history, and session data.

### 1.3 AI Service (FastAPI + RAG Pipeline)
- **Natural Language Processing**: Google Gemini 1.5/2.0 for context-aware MCQ generation.
- **Vector Search**: FAISS (Facebook AI Similarity Search) with `sentence-transformers` (all-MiniLM-L6-v2) for intelligent retrieval of document context.
- **Extensibility**: Custom endpoints for both file-based RAG and direct text-to-MCQ generation.

---

## 2. Key Features

- **Personalized Learning**: Users upload their own syllabi or notes; the AI generates questions tailored exactly to that content.
- **Real-Time 1v1 Battles**: Competitive matchmaking where speed and accuracy determine the winner.
- **Competition Module**: A classroom-scale module where teachers can host sessions with hundreds of participants, including a **Spectator Mode** for late joiners.
- **Privacy & Cleanup**: Automatic data purging of uploaded files and generated questions after game completion to ensure data security.
- **Server-Authoritative Timing**: Prevents cheating by calculating scores based on server-side timestamps.

---

## 3. Critical Improvements & Refactoring (April 2026 Audit)

Recent maintainability and stability audits identified and resolved two critical architectural flaws:

### 3.1 WebSocket Stability (Bug Fix)
- **Issue**: A method overloading conflict in the Javascript `SocketService` class caused an infinite recursive loop during the connection handshake.
- **Solution**: Refactored the `SocketService` to use a singular, robust `connect()` protocol. This eliminated browser-side crashes and stabilized real-time player synchronization.

### 3.2 Competition QA Generation (Feature Fix)
- **Issue**: The competition module failed to generate questions because it attempted to use a file-based RAG endpoint without a pre-indexed vector store.
- **Solution**: Implemented a new **Direct Text Generation** endpoint in the AI service. This allows the backend to pass raw textual context extracted from session resources directly to the LLM, ensuring guaranteed question generation for any session content.

---

## 4. Database Schema Overview

| Collection | Purpose |
| :--- | :--- |
| `users` | Stores accounts, hashes, and cumulative stats. |
| `game_history` | Historical record of 1v1 matches. |
| `competition_rooms` | Active and past larger-scale quiz sessions. |
| `competition_participants` | Real-time tracking of player scores and roles within a competition. |
| `student_questions` | AI-generated questions specific to competition sessions. |

---

## 5. Deployment & Execution

The project is designed as a microservice architecture:
1. **Primary Backend**: `python backend/main.py` (Port 8000)
2. **AI Microservice**: `python backend/ai-service/main.py` (Port 8001)
3. **Frontend Application**: `npm run dev` (Port 5173)

---

## 6. Future Roadmap
- **Analytics Dashboard**: Detailed performance metrics for teachers to identify "blind spots" in student comprehension.
- **Alternative LLM Support**: Built-in support for Anthropic Claude and OpenAI GPT-4.
- **Mobile Application**: Porting the frontend to React Native for mobile-first learning.

---
**Report generated for:** 1v1-RAG-Quiz Project Maintenance Phase
**Prepared by:** Antigravity AI (Advanced Agentic Coding Group)
