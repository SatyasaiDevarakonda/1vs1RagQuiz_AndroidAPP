"""
Quiz Battle API - FastAPI Backend with Guest Mode Support
"""
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from bson import ObjectId
import httpx
import json
import os

from database import connect_to_mongo, close_mongo_connection, get_database, init_competition_collections
from models import UserCreate, UserLogin, ProfileUpdate, PasswordChange, EmailChange
from auth import verify_password, get_password_hash, create_access_token, decode_access_token, create_guest_token
from game_manager import connection_manager, game_manager
from competition import router as competition_router


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    await connect_to_mongo()
    await init_competition_collections()
    print("Backend API ready on http://localhost:8000")
    yield
    await close_mongo_connection()


# ==================== APP SETUP ====================

app = FastAPI(
    title="Quiz Battle API",
    description="Real-time 1v1 Quiz Battle Platform with Guest Mode",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Competition routes
app.include_router(competition_router)


# ==================== HELPERS ====================

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Extract user from JWT token (works for both registered and guest users)"""
    if not authorization:
        return None
    
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        is_guest = payload.get("is_guest", False)
        
        if not user_id:
            return None
        
        # For guest users, return minimal user object
        if is_guest:
            return {
                "_id": user_id,
                "username": payload.get("username", "Guest"),
                "email": None,
                "is_guest": True,
                "games_played": 0,
                "games_won": 0,
                "total_score": 0,
                "created_at": datetime.utcnow()
            }
        
        # For registered users, fetch from database
        db = get_database()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["is_guest"] = False
        return user
    except Exception:
        return None


def format_user(user: dict) -> dict:
    """Format user for API response"""
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user.get("email"),
        "is_guest": user.get("is_guest", False),
        "games_played": user.get("games_played", 0),
        "games_won": user.get("games_won", 0),
        "total_score": user.get("total_score", 0),
        "created_at": user.get("created_at", datetime.utcnow()).isoformat()
    }


# ==================== AUTH ROUTES ====================

@app.post("/api/auth/signup")
async def signup(user_data: UserCreate):
    """Register a new user"""
    db = get_database()
    
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    existing = await db.users.find_one({"username": user_data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user_doc = {
        "username": user_data.username,
        "email": user_data.email.lower(),
        "password_hash": get_password_hash(user_data.password),
        "games_played": 0,
        "games_won": 0,
        "total_score": 0,
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Create token
    token = create_access_token({"sub": str(result.inserted_id)})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": format_user(user_doc)
    }


@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    """Login user"""
    db = get_database()
    
    user = await db.users.find_one({"email": credentials.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user["_id"])})
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": format_user(user)
    }


@app.post("/api/auth/guest")
async def guest_login():
    """
    Create a guest session
    Returns a temporary token with auto-generated username
    Guest data is NOT saved to database
    """
    import random
    
    # Generate unique guest username
    guest_id = str(uuid.uuid4())
    guest_username = f"Guest_{random.randint(1000, 9999)}"
    
    # Create guest token (no database entry)
    token = create_guest_token({
        "sub": guest_id,
        "username": guest_username,
        "is_guest": True
    })
    
    # Return guest user data
    guest_user = {
        "_id": guest_id,
        "username": guest_username,
        "email": None,
        "is_guest": True,
        "games_played": 0,
        "games_won": 0,
        "total_score": 0,
        "created_at": datetime.utcnow()
    }
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": format_user(guest_user)
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user (works for both registered and guest)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {"user": format_user(user)}


# ==================== PROFILE ROUTES ====================

@app.put("/api/profile/update")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Update user profile (registered users only)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest users cannot update profile")
    
    db = get_database()
    update_data = {}
    
    if data.username:
        # Check if username taken
        existing = await db.users.find_one({
            "username": data.username,
            "_id": {"$ne": user["_id"]}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        update_data["username"] = data.username
    
    if update_data:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )
    
    # Get updated user
    updated_user = await db.users.find_one({"_id": user["_id"]})
    return {"user": format_user(updated_user)}


@app.put("/api/profile/change-password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password (registered users only)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest users cannot change password")
    
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    db = get_database()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": get_password_hash(data.new_password)}}
    )
    
    return {"message": "Password changed successfully"}


@app.put("/api/profile/change-email")
async def change_email(data: EmailChange, user: dict = Depends(get_current_user)):
    """Change user email (registered users only)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest users cannot change email")
    
    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    
    db = get_database()
    
    # Check if email taken
    existing = await db.users.find_one({
        "email": data.new_email.lower(),
        "_id": {"$ne": user["_id"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"email": data.new_email.lower()}}
    )
    
    updated_user = await db.users.find_one({"_id": user["_id"]})
    return {"user": format_user(updated_user)}


@app.get("/api/profile/history")
async def get_game_history(user: dict = Depends(get_current_user)):
    """Get user's game history (registered users only)"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        # Guest users have no persistent history
        return {"history": []}
    
    db = get_database()
    history = await db.game_history.find(
        {"user_id": str(user["_id"])}
    ).sort("played_at", -1).limit(20).to_list(20)
    
    return {
        "history": [
            {
                "id": str(h["_id"]),
                "roomCode": h["room_code"],
                "mode": h["mode"],
                "score": h["score"],
                "totalQuestions": h["total_questions"],
                "correctAnswers": h["correct_answers"],
                "opponentUsername": h.get("opponent_username"),
                "opponentScore": h.get("opponent_score"),
                "result": h["result"],
                "playedAt": h["played_at"].isoformat()
            }
            for h in history
        ]
    }


# ==================== GAME ROUTES ====================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "message": "Quiz Battle server is running"}


@app.get("/api/questions/count")
async def get_question_count():
    """Get total question count"""
    db = get_database()
    count = await db.questions.count_documents({})
    return {"count": count}


@app.post("/api/rooms/create-with-pdf")
async def create_room_with_pdf(
    file: UploadFile = File(...),
    questions_count: int = Form(5),
    time_per_question: int = Form(15),
    difficulty: str = Form("medium"),
    mode: str = Form("multiplayer"),
    user: dict = Depends(get_current_user)
):
    """
    Create a room with PDF upload for question generation
    This replaces the WebSocket room creation for AI-powered games
    """
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Validate file type
    if not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are allowed")
    
    try:
        import os
        AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
        
        # Generate room code
        import random
        room_code = str(random.randint(1000, 9999))
        while room_code in game_manager.rooms:
            room_code = str(random.randint(1000, 9999))
        
        # Upload PDF to AI service with room_code
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Upload syllabus
            files = {"file": (file.filename, await file.read(), file.content_type)}
            data = {"room_code": room_code}
            
            upload_response = await client.post(
                f"{AI_SERVICE_URL}/upload-syllabus",
                files=files,
                data=data
            )
            
            if upload_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to upload syllabus to AI service")
            
            upload_data = upload_response.json()
            
            # Generate questions
            gen_response = await client.post(
                f"{AI_SERVICE_URL}/generate-questions",
                json={
                    "room_code": room_code,
                    "topic": "General",
                    "num_questions": questions_count,
                    "difficulty": difficulty
                }
            )
            
            if gen_response.status_code != 200:
                # Cleanup uploaded data
                await client.delete(f"{AI_SERVICE_URL}/rooms/{room_code}/cleanup")
                raise HTTPException(status_code=500, detail="Failed to generate questions")
            
            questions = gen_response.json()
            
            if len(questions) < questions_count:
                print(f"⚠️  Only generated {len(questions)}/{questions_count} questions")
            
            # Format questions for game manager
            formatted_questions = []
            for q in questions:
                formatted_questions.append({
                    "id": f"ai_{room_code}_{len(formatted_questions)}",
                    "question": q["question"],
                    "options": q["options"],
                    "correct_answer": q["correct_answer"],
                    "category": q.get("metadata", {}).get("topic", "AI Generated")
                })
            
            # Create room in game manager with pre-generated questions
            user_id = str(user["_id"]) if not user.get("is_guest") else user["_id"]
            username = user["username"]
            
            # Store room with questions
            game_manager.rooms[room_code] = {
                "code": room_code,
                "mode": mode,
                "status": "waiting",
                "players": [],
                "settings": {
                    "questionsCount": len(formatted_questions),
                    "timePerQuestion": time_per_question
                },
                "questions": formatted_questions,
                "current_question_index": 0,
                "question_start_time": None,
                "created_at": datetime.utcnow(),
                "host_socket_id": None,  # Will be set when host connects via WebSocket
                "host_user_id": user_id,
                "game_ended": False,
                "pdf_filename": file.filename,
                "ai_generated": True  # Flag to trigger cleanup
            }
            
            return {
                "room_code": room_code,
                "questions_generated": len(formatted_questions),
                "pdf_filename": file.filename,
                "message": "Room created successfully. Join via WebSocket to start."
            }
    
    except httpx.HTTPError as e:
        print(f"❌ AI Service error: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        print(f"❌ Error creating room with PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rooms/{room_code}/exists")
async def check_room_exists(room_code: str):
    """Check if a room exists and is joinable"""
    exists = room_code in game_manager.rooms
    joinable = False
    
    if exists:
        room = game_manager.rooms[room_code]
        joinable = room["status"] == "waiting" and len(room["players"]) < 2
    
    return {"exists": exists, "joinable": joinable}


# ==================== WEBSOCKET ====================


async def handle_join_competition(websocket: WebSocket, socket_id: str, payload: dict, user_id: Optional[str], username: str):
    """Handle joining a competition room via WebSocket"""
    if not user_id:
        await websocket.send_json({"event": "error", "data": {"message": "Authentication required"}})
        return
    
    room_code = payload.get("roomCode")
    role = payload.get("role", "player")
    
    if not room_code:
        await websocket.send_json({"event": "error", "data": {"message": "Room code required"}})
        return
    
    db = get_database()
    
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        await websocket.send_json({"event": "error", "data": {"message": "Room not found"}})
        return
    
    connection_manager.add_competition_connection(room_code.upper(), socket_id, websocket)
    websocket.competition_room_code = room_code.upper()
    websocket.competition_user_id = user_id
    websocket.competition_username = username
    
    participants = await db.competition_participants.find({
        "room_id": room["_id"]
    }).sort("score", -1).to_list(length=100)
    
    participant_ids = [ObjectId(p["student_id"]) for p in participants if ObjectId.is_valid(p["student_id"])]
    users = await db.users.find({"_id": {"$in": participant_ids}}).to_list(length=100)
    user_map = {str(u["_id"]): u["username"] for u in users}
    
    formatted_participants = []
    for p in participants:
        formatted_participants.append({
            "student_id": p["student_id"],
            "display_name": user_map.get(p["student_id"], "Unknown"),
            "role": p["role"],
            "score": p.get("score", 0),
            "correct_count": p.get("correct_count", 0)
        })
    
    await websocket.send_json({
        "event": "competition_player_joined",
        "data": {"participants": formatted_participants}
    })
    
    connection_manager.broadcast_to_competition_room(
        room_code.upper(),
        "competition_participant_joined",
        {"participants": formatted_participants}
    )


async def handle_start_competition(websocket: WebSocket, socket_id: str, payload: dict, user_id: Optional[str]):
    """Handle starting a competition"""
    if not user_id:
        await websocket.send_json({"event": "error", "data": {"message": "Authentication required"}})
        return
    
    room_code = payload.get("roomCode")
    
    db = get_database()
    
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        await websocket.send_json({"event": "error", "data": {"message": "Room not found"}})
        return
    
    if str(room.get("created_by")) != user_id:
        await websocket.send_json({"event": "error", "data": {"message": "Only the room creator can start"}})
        return
    
    if room["status"] != "waiting":
        await websocket.send_json({"event": "error", "data": {"message": "Competition already started"}})
        return
    
    teacher_polls = []
    if room.get("teacher_poll_ids"):
        poll_ids = [ObjectId(pid) for pid in room["teacher_poll_ids"]]
        teacher_polls = await db.polls.find({
            "_id": {"$in": poll_ids},
            "correct_answer": {"$ne": None}
        }).to_list(length=100)
    elif room.get("teacher_question_count", 0) > 0:
        session = await db.sessions.find_one({"session_id": room["session_id"]})
        if session:
            teacher_polls = await db.polls.find({
                "session_id": session["_id"],
                "correct_answer": {"$ne": None}
            }).limit(room["teacher_question_count"]).to_list(length=100)
    
    student_questions = []
    if room.get("student_question_ids"):
        sq_ids = [ObjectId(sid) for sid in room["student_question_ids"]]
        student_questions = await db.student_questions.find({
            "_id": {"$in": sq_ids}
        }).to_list(length=100)
    else:
        student_questions = await db.student_questions.find({
            "session_id": room["session_id"]
        }).to_list(length=100)
    
    total_questions = min(room.get("total_questions", 0), len(teacher_polls) + len(student_questions))
    all_questions = teacher_polls[:room.get("teacher_question_count", len(teacher_polls))]
    
    remaining_slots = total_questions - len(all_questions)
    if remaining_slots > 0:
        all_questions.extend(student_questions[:remaining_slots])
    
    if not all_questions:
        await websocket.send_json({"event": "error", "data": {"message": "No questions available"}})
        return
    
    game_manager.competition_room_state[room_code.upper()] = {
        "status": "active",
        "current_question_index": -1,
        "question_start_time": None,
        "all_questions": all_questions,
        "time_per_question": room.get("time_per_question", 20),
        "total_questions": len(all_questions),
        "timer_handles": []
    }
    
    await db.competition_rooms.update_one(
        {"_id": room["_id"]},
        {"$set": {"status": "active", "total_questions": len(all_questions), "started_at": datetime.utcnow()}}
    )
    
    connection_manager.broadcast_to_competition_room(
        room_code.upper(),
        "competition_started",
        {"total_questions": len(all_questions)}
    )
    
    await reveal_next_competition_question(room_code.upper())


async def reveal_next_competition_question(room_code: str):
    """Reveal the next question in a competition"""
    state = game_manager.competition_room_state.get(room_code)
    if not state:
        return
    
    state["current_question_index"] += 1
    
    if state["current_question_index"] >= state["total_questions"]:
        await end_competition(room_code)
        return
    
    q = state["all_questions"][state["current_question_index"]]
    state["question_start_time"] = game_manager.get_server_time()
    question_index = state["current_question_index"]
    
    db = get_database()
    room = await db.competition_rooms.find_one({"room_code": room_code})
    if room:
        await db.competition_rooms.update_one(
            {"_id": room["_id"]},
            {"$set": {"current_question_index": question_index, "question_start_time": state["question_start_time"]}}
        )
    
    question_data = {
        "question_index": question_index,
        "total_questions": state["total_questions"],
        "question": q.get("question"),
        "options": q.get("options", []),
        "time_per_question": state["time_per_question"],
        "question_start_time": state["question_start_time"],
        "end_time": state["question_start_time"] + state["time_per_question"] * 1000
    }
    
    connection_manager.broadcast_to_competition_room(
        room_code,
        "competition_question",
        question_data
    )
    
    async def reveal_after_timer():
        try:
            db = get_database()
            room = await db.competition_rooms.find_one({"room_code": room_code})
            
            scores = []
            if room:
                participants = await db.competition_participants.find({
                    "room_id": room["_id"],
                    "role": "player"
                }).sort("score", -1).to_list(length=100)
                
                participant_ids = [ObjectId(p["student_id"]) for p in participants if ObjectId.is_valid(p["student_id"])]
                users = await db.users.find({"_id": {"$in": participant_ids}}).to_list(length=100)
                user_map = {str(u["_id"]): u["username"] for u in users}
                
                for idx, p in enumerate(participants):
                    scores.append({
                        "student_id": p["student_id"],
                        "display_name": user_map.get(p["student_id"], "Unknown"),
                        "score": p.get("score", 0),
                        "correct_count": p.get("correct_count", 0),
                        "questions_answered": p.get("questions_answered", 0),
                        "rank": idx + 1
                    })
            
            connection_manager.broadcast_to_competition_room(
                room_code,
                "competition_answer_reveal",
                {
                    "question_index": question_index,
                    "question": q.get("question"),
                    "options": q.get("options", []),
                    "correct_index": q.get("correct_answer", 0),
                    "explanation": q.get("justification", ""),
                    "scores": scores
                }
            )
            
            await asyncio.sleep(3)
            await reveal_next_competition_question(room_code)
            
        except Exception as e:
            print(f"Error in competition reveal: {e}")
    
    timer_task = asyncio.create_task(reveal_after_timer())
    state["timer_handles"].append(timer_task)


async def handle_competition_answer(websocket: WebSocket, socket_id: str, payload: dict, user_id: Optional[str]):
    """Handle answer submission in a competition"""
    if not user_id:
        return
    
    room_code = payload.get("roomCode")
    answer_index = payload.get("answerIndex")
    question_index = payload.get("questionIndex")
    
    state = game_manager.competition_room_state.get(room_code)
    if not state or state["status"] != "active":
        return
    
    response_time_ms = min(
        game_manager.get_server_time() - (state["question_start_time"] or game_manager.get_server_time()),
        state["time_per_question"] * 1000
    )
    
    q = state["all_questions"][question_index]
    if not q:
        return
    
    is_correct = answer_index == q.get("correct_answer")
    points_earned = 0
    
    if is_correct:
        base_points = 100
        speed_bonus = int(max(0, (state["time_per_question"] * 1000 - response_time_ms) / (state["time_per_question"] * 1000)) * 50)
        points_earned = base_points + speed_bonus
    
    db = get_database()
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        return
    
    room_id = room["_id"]
    
    await db.competition_answers.update_one(
        {"room_id": room_id, "student_id": user_id, "question_index": question_index},
        {
            "$set": {
                "room_id": room_id,
                "student_id": user_id,
                "question_index": question_index,
                "answer_index": answer_index,
                "is_correct": is_correct,
                "response_time_ms": response_time_ms,
                "points_earned": points_earned,
                "answered_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    if is_correct:
        await db.competition_participants.update_one(
            {"room_id": room_id, "student_id": user_id},
            {
                "$inc": {"score": points_earned, "correct_count": 1, "questions_answered": 1}
            }
        )
    else:
        await db.competition_participants.update_one(
            {"room_id": room_id, "student_id": user_id},
            {"$inc": {"questions_answered": 1}}
        )
    
    answered_count = await db.competition_answers.count_documents({
        "room_id": room_id,
        "question_index": question_index
    })
    
    player_count = await db.competition_participants.count_documents({
        "room_id": room_id,
        "role": "player"
    })
    
    connection_manager.broadcast_to_competition_room(
        room_code.upper(),
        "competition_answer_received",
        {"answered_count": answered_count, "total_players": player_count}
    )


def handle_leave_competition(socket_id: str, payload: dict, user_id: Optional[str]):
    """Handle leaving a competition room"""
    room_code = payload.get("roomCode")
    if room_code:
        connection_manager.remove_competition_connection(room_code.upper(), socket_id)


async def end_competition(room_code: str):
    """End a competition and broadcast final results"""
    state = game_manager.competition_room_state.get(room_code)
    if state:
        for handle in state.get("timer_handles", []):
            handle.cancel()
        state["timer_handles"] = []
    
    db = get_database()
    room = await db.competition_rooms.find_one({"room_code": room_code})
    
    if room:
        await db.competition_rooms.update_one(
            {"_id": room["_id"]},
            {"$set": {"status": "finished", "ended_at": datetime.utcnow()}}
        )
    
    participants = await db.competition_participants.find({
        "room_id": room["_id"] if room else None,
        "role": "player"
    }).sort("score", -1).to_list(length=100)
    
    if room:
        participant_ids = [ObjectId(p["student_id"]) for p in participants if ObjectId.is_valid(p["student_id"])]
        users = await db.users.find({"_id": {"$in": participant_ids}}).to_list(length=100)
        user_map = {str(u["_id"]): u["username"] for u in users}
    
    leaderboard = []
    for idx, p in enumerate(participants):
        questions_answered = p.get("questions_answered", 0)
        accuracy = round((p.get("correct_count", 0) / questions_answered * 100), 1) if questions_answered > 0 else 0
        
        leaderboard.append({
            "student_id": p["student_id"],
            "display_name": user_map.get(p["student_id"], "Unknown") if room else "Unknown",
            "score": p.get("score", 0),
            "correct_count": p.get("correct_count", 0),
            "questions_answered": questions_answered,
            "accuracy": accuracy,
            "rank": idx + 1
        })
    
    connection_manager.broadcast_to_competition_room(
        room_code,
        "competition_finished",
        {"leaderboard": leaderboard}
    )
    
    game_manager.competition_room_state.pop(room_code, None)
    print(f"Competition ended: {room_code}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time game communication"""
    socket_id = str(uuid.uuid4())
    await connection_manager.connect(websocket, socket_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {
                "socketId": socket_id,
                "serverTime": game_manager.get_server_time()
            }
        })
        
        while True:
            data = await websocket.receive_json()
            event = data.get("event")
            payload = data.get("data", {})
            
            # Get user info from token (supports both guest and registered)
            token = payload.get("token")
            user_id = None
            username = payload.get("username", "Guest")
            is_guest = False
            
            if token:
                decoded = decode_access_token(token)
                if decoded:
                    user_id = decoded.get("sub")
                    username = decoded.get("username", username)
                    is_guest = decoded.get("is_guest", False)
                    
                    # For registered users, fetch username from database
                    if not is_guest:
                        db = get_database()
                        user = await db.users.find_one({"_id": ObjectId(user_id)})
                        if user:
                            username = user["username"]
            
            # Handle events
            if event == "create_room":
                await game_manager.create_room(
                    socket_id,
                    user_id,
                    username,
                    payload.get("mode", "multiplayer"),
                    payload.get("settings")
                )
            
            elif event == "join_room":
                await game_manager.join_room(
                    socket_id,
                    payload.get("roomCode"),
                    user_id,
                    username
                )
            
            elif event == "toggle_ready":
                await game_manager.toggle_ready(
                    socket_id,
                    payload.get("roomCode")
                )
            
            elif event == "submit_answer":
                await game_manager.submit_answer(
                    socket_id,
                    payload.get("roomCode"),
                    payload.get("answer")
                )
            
            elif event == "join_competition":
                await handle_join_competition(websocket, socket_id, payload, user_id, username)
            
            elif event == "start_competition":
                await handle_start_competition(websocket, socket_id, payload, user_id)
            
            elif event == "competition_answer":
                await handle_competition_answer(websocket, socket_id, payload, user_id)
            
            elif event == "leave_competition":
                handle_leave_competition(socket_id, payload, user_id)
    
    except WebSocketDisconnect:
        await game_manager.handle_disconnect(socket_id)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        await game_manager.handle_disconnect(socket_id)


# ==================== STATIC FILES ====================

import os
from pathlib import Path

# Check if frontend build exists
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
FRONTEND_BUILD_EXISTS = FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists()

if FRONTEND_BUILD_EXISTS:
    # Production mode: Serve built frontend
    print("✅ Serving built frontend from /frontend/dist")
    
    # Mount static assets
    try:
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    except Exception as e:
        print(f"⚠️  Could not mount /assets: {e}")

    @app.get("/favicon.ico")
    async def favicon():
        """Serve favicon"""
        favicon_path = FRONTEND_DIST / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        else:
            return Response(status_code=404)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA for all other routes"""
        # Don't serve index.html for API routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return Response(status_code=404)
        
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return Response(status_code=404)

else:
    # Development mode: Frontend runs on separate dev server
    print("🔧 Development mode: Frontend should run on http://localhost:5173")
    print("   Run 'cd frontend && npm run dev' in a separate terminal")
    
    @app.get("/")
    async def root():
        """Root endpoint - helpful message in dev mode"""
        return {
            "message": "1v1 RAG Quiz - Backend API",
            "status": "running",
            "mode": "development",
            "frontend": "http://localhost:5173",
            "backend": "http://localhost:8000",
            "api_docs": "http://localhost:8000/docs",
            "ai_service": "http://localhost:8001",
            "note": "Frontend is running separately on Vite dev server"
        }
    
    @app.get("/favicon.ico")
    async def favicon():
        """Return 204 No Content for favicon in dev mode"""
        return Response(status_code=204)


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)