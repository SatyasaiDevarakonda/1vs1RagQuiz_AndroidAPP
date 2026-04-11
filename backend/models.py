"""
Pydantic Models for Quiz Battle
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class GameMode(str, Enum):
    SINGLE = "single"
    MULTIPLAYER = "multiplayer"


class GameStatus(str, Enum):
    WAITING = "waiting"
    COUNTDOWN = "countdown"
    PLAYING = "playing"
    FINISHED = "finished"


# Auth Models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    games_played: int = 0
    games_won: int = 0
    total_score: int = 0
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Profile Models
class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=20)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class EmailChange(BaseModel):
    new_email: EmailStr
    password: str


# Game Models
class GameSettings(BaseModel):
    questionsCount: int = 5
    timePerQuestion: int = 15


class Question(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: str
    category: str = "General"


class Player(BaseModel):
    socket_id: str
    user_id: Optional[str] = None
    username: str
    score: int = 0
    current_answer: Optional[str] = None
    is_ready: bool = False
    is_connected: bool = True


class Room(BaseModel):
    code: str
    mode: GameMode
    status: GameStatus
    players: List[Player]
    settings: GameSettings
    questions: List[Question] = []
    current_question_index: int = 0
    created_at: datetime
    host_socket_id: str


class GameHistory(BaseModel):
    user_id: str
    room_code: str
    mode: str
    score: int
    total_questions: int
    correct_answers: int
    opponent_username: Optional[str] = None
    opponent_score: Optional[int] = None
    result: str  # "win", "loss", "draw", "completed"
    played_at: datetime
