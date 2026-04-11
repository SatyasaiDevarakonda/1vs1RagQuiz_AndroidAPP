"""
Competition Routes - Room management, leaderboard, AI question generation
"""
import random
import string
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header
from bson import ObjectId
import httpx

from database import get_database
from auth import decode_access_token


router = APIRouter(prefix="/api/competition", tags=["competition"])


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from token"""
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
        
        db = get_database()
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["is_guest"] = False
        return user
    except Exception:
        return None


def generate_room_code() -> str:
    """Generate a 6-character room code starting with 'C'"""
    chars = string.ascii_uppercase + string.digits
    code = 'C'
    for _ in range(5):
        code += random.choice(chars)
    return code


def letter_to_index(letter: str) -> int:
    """Convert letter to index: A=0, B=1, C=2, D=3"""
    if letter == 'B':
        return 1
    if letter == 'C':
        return 2
    if letter == 'D':
        return 3
    return 0


async def get_current_user_optional(authorization: Optional[str] = None):
    """Get current user or None"""
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "")
        return await get_current_user(authorization)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/competition/rooms
# Create a new competition room
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/rooms")
async def create_competition_room(
    session_id: str,
    time_per_question: int = 20,
    teacher_question_count: int = 0,
    student_question_ids: List[str] = None,
    user: dict = Depends(get_current_user)
):
    """Create a new competition room"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest users cannot create competition rooms")
    
    db = get_database()
    
    # Validate session exists
    session = await db.sessions.find_one({"session_id": session_id.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user is enrolled (teacher or participant)
    user_id = str(user["_id"])
    is_teacher = str(session.get("teacher_id")) == user_id
    
    if not is_teacher:
        participant = await db.session_participants.find_one({
            "session_id": session["_id"],
            "student_id": user_id
        })
        if not participant:
            raise HTTPException(status_code=403, detail="You are not enrolled in this session")
    
    # Get teacher polls (questions with correct_answer)
    teacher_polls = []
    if teacher_question_count > 0:
        polls_cursor = db.polls.find({
            "session_id": session["_id"],
            "correct_answer": {"$ne": None}
        }).limit(teacher_question_count)
        teacher_polls = await polls_cursor.to_list(length=teacher_question_count)
    
    # Get student questions (AI generated)
    student_questions = []
    if student_question_ids:
        obj_ids = [ObjectId(qid) for qid in student_question_ids if qid]
        student_questions = await db.student_questions.find({
            "_id": {"$in": obj_ids},
            "session_id": session_id.upper()
        }).to_list(length=len(obj_ids))
    else:
        student_questions = await db.student_questions.find({
            "session_id": session_id.upper()
        }).to_list(length=100)
    
    total_questions = len(teacher_polls) + len(student_questions)
    if total_questions == 0:
        raise HTTPException(
            status_code=400,
            detail="No questions available. Add polls or generate AI questions first."
        )
    
    # Generate unique room code
    room_code = generate_room_code()
    for _ in range(10):
        existing = await db.competition_rooms.find_one({"room_code": room_code})
        if not existing:
            break
        room_code = generate_room_code()
    
    # Create room
    room_doc = {
        "room_code": room_code,
        "session_id": session_id.upper(),
        "created_by": user_id,
        "status": "waiting",
        "current_question_index": -1,
        "question_start_time": None,
        "time_per_question": min(60, max(10, time_per_question)),
        "total_questions": total_questions,
        "teacher_question_count": len(teacher_polls),
        "student_question_ids": [str(q["_id"]) for q in student_questions],
        "teacher_poll_ids": [str(p["_id"]) for p in teacher_polls],
        "started_at": None,
        "ended_at": None,
        "created_at": datetime.utcnow()
    }
    
    result = await db.competition_rooms.insert_one(room_doc)
    room_doc["_id"] = result.inserted_id
    
    # Auto-join creator as player
    await db.competition_participants.update_one(
        {"room_id": room_doc["_id"], "student_id": user_id},
        {
            "$set": {
                "room_id": room_doc["_id"],
                "student_id": user_id,
                "role": "player",
                "score": 0,
                "correct_count": 0,
                "questions_answered": 0,
                "joined_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    return {
        "room_code": room_code,
        "session_id": session_id.upper(),
        "total_questions": total_questions,
        "time_per_question": room_doc["time_per_question"]
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/competition/rooms/active
# Get active competition rooms
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/rooms/active")
async def get_active_rooms(user: dict = Depends(get_current_user_optional)):
    """Get all active/waiting competition rooms"""
    db = get_database()
    
    cursor = db.competition_rooms.aggregate([
        {"$match": {"status": {"$in": ["waiting", "active"]}}},
        {"$lookup": {
            "from": "users",
            "localField": "created_by",
            "foreignField": "_id",
            "as": "creator"
        }},
        {"$lookup": {
            "from": "sessions",
            "localField": "session_id",
            "foreignField": "session_id",
            "as": "session"
        }},
        {"$lookup": {
            "from": "competition_participants",
            "localField": "_id",
            "foreignField": "room_id",
            "as": "participants"
        }},
        {"$unwind": {"path": "$creator", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$session", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id": {"$toString": "$_id"},
            "room_code": 1,
            "session_id": 1,
            "status": 1,
            "time_per_question": 1,
            "total_questions": 1,
            "created_at": 1,
            "session_title": {"$arrayElemAt": ["$session.title", 0]},
            "course_name": {"$arrayElemAt": ["$session.course_name", 0]},
            "creator_name": {"$arrayElemAt": ["$creator.username", 0]},
            "player_count": {
                "$size": {
                    "$filter": {
                        "input": "$participants",
                        "as": "p",
                        "cond": {"$eq": ["$p.role", "player"]}
                    }
                }
            }
        }},
        {"$sort": {"created_at": -1}}
    ])
    
    rooms = await cursor.to_list(length=100)
    return {"rooms": rooms}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/competition/rooms/{room_code}
# Get room details
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/rooms/{room_code}")
async def get_competition_room(room_code: str, user: dict = Depends(get_current_user_optional)):
    """Get competition room details"""
    db = get_database()
    
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Get session info
    session = await db.sessions.find_one({"session_id": room["session_id"]})
    
    # Get participants
    participants = await db.competition_participants.find({
        "room_id": room["_id"]
    }).sort("score", -1).to_list(length=100)
    
    # Get user details for participants
    participant_ids = [p["student_id"] for p in participants]
    valid_ids = [ObjectId(uid) for uid in participant_ids if ObjectId.is_valid(uid)]
    user_map = {}
    
    if valid_ids:
        users_cursor = db.users.find({"_id": {"$in": valid_ids}})
        users = await users_cursor.to_list(length=100)
        user_map = {str(u["_id"]): u["username"] for u in users}
    
    formatted_participants = []
    for p in participants:
        formatted_participants.append({
            "student_id": p["student_id"],
            "display_name": user_map.get(p["student_id"], "Unknown"),
            "role": p["role"],
            "score": p.get("score", 0),
            "correct_count": p.get("correct_count", 0),
            "questions_answered": p.get("questions_answered", 0),
            "joined_at": p.get("joined_at", "").isoformat() if p.get("joined_at") else None
        })
    
    return {
        "room": {
            "id": str(room["_id"]),
            "room_code": room["room_code"],
            "session_id": room["session_id"],
            "status": room["status"],
            "time_per_question": room.get("time_per_question", 20),
            "total_questions": room.get("total_questions", 0),
            "created_by": str(room.get("created_by", "")),
            "session_title": session.get("title") if session else "Unknown",
            "course_name": session.get("course_name") if session else "Unknown"
        },
        "participants": formatted_participants
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/competition/rooms/{room_code}/join
# Join a competition room
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/rooms/{room_code}/join")
async def join_competition_room(
    room_code: str,
    role: str = "player",
    user: dict = Depends(get_current_user)
):
    """Join a competition room"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db = get_database()
    
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room["status"] == "finished":
        raise HTTPException(status_code=400, detail="Competition has already ended")
    
    # Active rooms force spectator role
    if room["status"] == "active":
        role = "spectator"
    
    final_role = "spectator" if role == "spectator" else "player"
    
    user_id = str(user["_id"])
    
    # Check enrollment
    session = await db.sessions.find_one({"session_id": room["session_id"]})
    if session:
        is_teacher = str(session.get("teacher_id")) == user_id
        if not is_teacher:
            participant = await db.session_participants.find_one({
                "session_id": session["_id"],
                "student_id": user_id
            })
            if not participant:
                raise HTTPException(status_code=403, detail="You are not enrolled in this session")
    
    # Add participant (idempotent)
    await db.competition_participants.update_one(
        {"room_id": room["_id"], "student_id": user_id},
        {
            "$set": {
                "room_id": room["_id"],
                "student_id": user_id,
                "role": final_role,
                "joined_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    # Get updated participant
    participant = await db.competition_participants.find_one({
        "room_id": room["_id"],
        "student_id": user_id
    })
    
    return {
        "room": {
            "room_code": room["room_code"],
            "session_id": room["session_id"],
            "status": room["status"],
            "time_per_question": room.get("time_per_question", 20),
            "total_questions": room.get("total_questions", 0)
        },
        "participant": {
            "role": participant["role"],
            "score": participant.get("score", 0),
            "correct_count": participant.get("correct_count", 0)
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/competition/rooms/{room_code}/leaderboard
# Get competition leaderboard
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/rooms/{room_code}/leaderboard")
async def get_competition_leaderboard(room_code: str, user: dict = Depends(get_current_user_optional)):
    """Get competition leaderboard"""
    db = get_database()
    
    room = await db.competition_rooms.find_one({"room_code": room_code.upper()})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    participants = await db.competition_participants.find({
        "room_id": room["_id"],
        "role": "player"
    }).sort("score", -1).to_list(length=100)
    
    # Get user names
    participant_ids = [ObjectId(p["student_id"]) for p in participants if ObjectId.is_valid(p["student_id"])]
    users_cursor = db.users.find({"_id": {"$in": participant_ids}})
    users = await users_cursor.to_list(length=100)
    user_map = {str(u["_id"]): u["username"] for u in users}
    
    leaderboard = []
    for idx, p in enumerate(participants):
        questions_answered = p.get("questions_answered", 0)
        accuracy = round((p.get("correct_count", 0) / questions_answered * 100), 1) if questions_answered > 0 else 0
        
        leaderboard.append({
            "student_id": p["student_id"],
            "display_name": user_map.get(p["student_id"], "Unknown"),
            "score": p.get("score", 0),
            "correct_count": p.get("correct_count", 0),
            "questions_answered": questions_answered,
            "accuracy": accuracy,
            "rank": idx + 1
        })
    
    return {"leaderboard": leaderboard}


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/competition/sessions/{session_id}/generate-questions
# Generate AI questions for a session
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/sessions/{session_id}/generate-questions")
async def generate_competition_questions(
    session_id: str,
    count: int = 5,
    file_ids: List[str] = None,
    user: dict = Depends(get_current_user)
):
    """Generate AI questions from session resources"""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest users cannot generate questions")
    
    db = get_database()
    
    # Check session exists and user is enrolled
    session = await db.sessions.find_one({"session_id": session_id.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_id = str(user["_id"])
    is_teacher = str(session.get("teacher_id")) == user_id
    
    if not is_teacher:
        participant = await db.session_participants.find_one({
            "session_id": session["_id"],
            "student_id": user_id
        })
        if not participant:
            raise HTTPException(status_code=403, detail="You are not enrolled in this session")
    
    # Get resources for this session
    resources = await db.resources.find({
        "session_id": session_id.upper()
    }).to_list(length=20)
    
    if not resources:
        raise HTTPException(
            status_code=400,
            detail="No session material found. Please upload resources first."
        )
    
    # Use AI service to generate questions
    try:
        import os
        AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")
        
        # Get content from resources (simplified - would need proper RAG)
        context = ""
        for r in resources[:3]:
            content = r.get("content", "") or r.get("text", "")
            if content:
                context += content[:2000] + "\n\n"
        
        if not context:
            raise HTTPException(
                status_code=400,
                detail="No readable content in session resources"
            )
        
        # Generate questions via AI
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/generate-questions-from-text",
                json={
                    "context": context[:6000],
                    "num_questions": count,
                    "topic": "Session Quiz",
                    "difficulty": "medium"
                }
            )
            
            if response.status_code != 200:
                print(f"AI error: {response.text}")
                raise HTTPException(status_code=500, detail="AI question generation failed")
            
            mcqs = response.json()
            if not isinstance(mcqs, list):
                mcqs = []
            
    except httpx.HTTPError as e:
        print(f"HTTPError connecting to AI service: {e}")
        # Fallback: create sample questions
        mcqs = []
        for i in range(count):
            mcqs.append({
                "question": f"Sample question {i+1} about {session.get('title', 'the topic')}?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "metadata": {"justification": "This is the correct answer."}
            })
    
    # Store questions
    inserted = []
    for mcq in mcqs:
        options = mcq.get("options", ["", "", "", ""])
        # Ensure we have 4 options
        while len(options) < 4:
            options.append(f"Option {len(options)+1}")
            
        correct_text = mcq.get("correct_answer", options[0])
        # Find index of correct_text in options list
        correct_index = 0
        try:
            if correct_text in options:
                correct_index = options.index(correct_text)
        except ValueError:
            correct_index = 0
            
        metadata = mcq.get("metadata", {})
            
        question_doc = {
            "session_id": session_id.upper(),
            "created_by": user_id,
            "question": mcq.get("question", ""),
            "options": options[:4],
            "correct_answer": correct_index,
            "justification": metadata.get("justification", ""),
            "source": "ai",
            "created_at": datetime.utcnow()
        }
        
        result = await db.student_questions.insert_one(question_doc)
        question_doc["_id"] = result.inserted_id
        inserted.append(question_doc)
    
    return {
        "generated": inserted,
        "count": len(inserted)
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/competition/sessions/{session_id}/questions
# Get all questions for a session
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/sessions/{session_id}/questions")
async def get_session_questions(session_id: str, user: dict = Depends(get_current_user_optional)):
    """Get teacher polls and AI-generated student questions for a session"""
    db = get_database()
    
    # Get teacher polls
    session = await db.sessions.find_one({"session_id": session_id.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    teacher_polls = await db.polls.find({
        "session_id": session["_id"],
        "correct_answer": {"$ne": None}
    }).to_list(length=100)
    
    # Get student questions
    student_questions = await db.student_questions.find({
        "session_id": session_id.upper()
    }).to_list(length=100)
    
    return {
        "teacher_poll_count": len(teacher_polls),
        "teacher_polls": teacher_polls,
        "student_questions": student_questions
    }