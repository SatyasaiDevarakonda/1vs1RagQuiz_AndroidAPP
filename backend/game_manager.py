"""
Game Manager - Server-Authoritative Game Logic
All timing, scoring, and game state managed on server
"""
import asyncio
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from fastapi import WebSocket
from bson import ObjectId

from database import get_database

# asyncio.create_task() only keeps a WEAK reference to the task it returns -
# if nothing else holds a reference, the task can be garbage-collected before
# it finishes, silently cancelling it mid-flight. This bit history saves and
# cleanup jobs intermittently. Route every fire-and-forget task through here
# so a strong reference is kept until it actually completes.
_background_tasks: Set[asyncio.Task] = set()


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


class ConnectionManager:
    """Manages WebSocket connections with proper state tracking"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.socket_to_room: Dict[str, str] = {}
        self.closed_sockets: Set[str] = set()
        self.competition_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.competition_room_state: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, socket_id: str):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[socket_id] = websocket
        self.closed_sockets.discard(socket_id)
        print(f"Client connected: {socket_id}")

    def disconnect(self, socket_id: str):
        """Remove a WebSocket connection"""
        self.closed_sockets.add(socket_id)
        if socket_id in self.active_connections:
            del self.active_connections[socket_id]
        if socket_id in self.socket_to_room:
            del self.socket_to_room[socket_id]
        print(f"Client disconnected: {socket_id}")

    def is_connected(self, socket_id: str) -> bool:
        """Check if socket is still connected"""
        if socket_id in self.closed_sockets:
            return False
        if socket_id not in self.active_connections:
            return False
        return True

    async def send_to_socket(self, socket_id: str, event: str, data: dict):
        """Send a message to a specific socket with safety checks"""
        if not self.is_connected(socket_id):
            return False

        try:
            websocket = self.active_connections.get(socket_id)
            if websocket:
                await websocket.send_json({
                    "event": event,
                    "data": data
                })
                return True
        except Exception as e:
            print(f"Send error {socket_id}: {e}")
            self.closed_sockets.add(socket_id)
            if socket_id in self.active_connections:
                del self.active_connections[socket_id]
        return False

    async def broadcast_to_room(self, room_code: str, event: str, data: dict, exclude: str = None):
        """Broadcast a message to all sockets in a room"""
        tasks = []
        for socket_id, code in list(self.socket_to_room.items()):
            if code == room_code and socket_id != exclude:
                tasks.append(self.send_to_socket(socket_id, event, data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_room(self, socket_id: str) -> Optional[str]:
        """Get the room code for a socket"""
        return self.socket_to_room.get(socket_id)

    def set_room(self, socket_id: str, room_code: str):
        """Set the room for a socket"""
        self.socket_to_room[socket_id] = room_code

    def broadcast_to_competition_room(self, room_code: str, event: str, data: dict):
        """Broadcast to all connections in a competition room"""
        if room_code not in self.competition_connections:
            return
        
        for socket_id, ws in self.competition_connections[room_code].items():
            if self.is_connected(socket_id):
                spawn(self.send_to_socket(socket_id, event, data))

    def add_competition_connection(self, room_code: str, socket_id: str, websocket: WebSocket):
        """Add a connection to a competition room"""
        if room_code not in self.competition_connections:
            self.competition_connections[room_code] = {}
        self.competition_connections[room_code][socket_id] = websocket

    def remove_competition_connection(self, room_code: str, socket_id: str):
        """Remove a connection from a competition room"""
        if room_code in self.competition_connections:
            self.competition_connections[room_code].pop(socket_id, None)
            if not self.competition_connections[room_code]:
                del self.competition_connections[room_code]


class GameManager:
    """Server-authoritative game management with speed-based scoring"""

    # Scoring constants
    BASE_POINTS = 100
    MAX_SPEED_BONUS = 100  # Max bonus for instant answer
    ANSWER_REVIEW_SECONDS = 3  # How long to show correct answer before next question

    def __init__(self, connection_manager: ConnectionManager):
        self.cm = connection_manager
        self.rooms: Dict[str, dict] = {}
        self.timers: Dict[str, asyncio.Task] = {}
        self.competition_room_state: Dict[str, dict] = {}

    def get_server_time(self) -> int:
        """Get current server timestamp in milliseconds"""
        return int(time.time() * 1000)

    def generate_room_code(self) -> str:
        """Generate a unique 4-digit room code"""
        while True:
            code = str(random.randint(1000, 9999))
            if code not in self.rooms:
                return code

    async def get_random_questions(self, count: int) -> List[dict]:
        """Get random questions from database"""
        db = get_database()
        pipeline = [{"$sample": {"size": count}}]
        questions = []
        async for q in db.questions.aggregate(pipeline):
            questions.append({
                "id": str(q["_id"]),
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "category": q.get("category", "General")
            })
        return questions

    def calculate_score(self, time_taken_ms: int, time_limit_ms: int) -> int:
        """
        Calculate score based on answer speed
        - Base points for correct answer
        - Speed bonus: faster = more points
        """
        if time_taken_ms >= time_limit_ms:
            return self.BASE_POINTS

        remaining_ratio = 1 - (time_taken_ms / time_limit_ms)
        speed_bonus = int(remaining_ratio * self.MAX_SPEED_BONUS)

        return self.BASE_POINTS + speed_bonus

    async def create_room(self, socket_id: str, user_id: Optional[str], username: str, mode: str, settings: dict = None):
        """Create a new game room"""
        room_code = self.generate_room_code()

        settings = settings or {"questionsCount": 5, "timePerQuestion": 15}

        player = {
            "socket_id": socket_id,
            "user_id": user_id,
            "username": username,
            "score": 0,
            "current_answer": None,
            "answer_time": None,
            "points_earned": 0,
            "is_ready": mode == "single",
            "is_connected": True,
            "correct_answers": 0
        }

        self.rooms[room_code] = {
            "code": room_code,
            "mode": mode,
            "status": "waiting",
            "players": [player],
            "settings": settings,
            "questions": [],
            "current_question_index": 0,
            "question_start_time": None,
            "created_at": datetime.utcnow(),
            "host_socket_id": socket_id,
            "game_ended": False
        }

        self.cm.set_room(socket_id, room_code)

        await self.cm.send_to_socket(socket_id, "room_created", {
            "roomCode": room_code,
            "mode": mode,
            "settings": settings,
            "players": [self._format_player(player)]
        })

        if mode == "single":
            await self.start_game(room_code)

    async def join_room(self, socket_id: str, room_code: str, user_id: Optional[str], username: str):
        """Join an existing room"""
        if room_code not in self.rooms:
            await self.cm.send_to_socket(socket_id, "error", {"message": "Room not found"})
            return

        room = self.rooms[room_code]

        if room["status"] != "waiting":
            await self.cm.send_to_socket(socket_id, "error", {"message": "Game already in progress"})
            return

        if len(room["players"]) >= 2:
            await self.cm.send_to_socket(socket_id, "error", {"message": "Room is full"})
            return

        for p in room["players"]:
            if p["socket_id"] == socket_id:
                await self.cm.send_to_socket(socket_id, "error", {"message": "Already in this room"})
                return

        is_single = room["mode"] == "single"

        player = {
            "socket_id": socket_id,
            "user_id": user_id,
            "username": username,
            "score": 0,
            "current_answer": None,
            "answer_time": None,
            "points_earned": 0,
            "is_ready": is_single,
            "is_connected": True,
            "correct_answers": 0
        }

        room["players"].append(player)
        self.cm.set_room(socket_id, room_code)

        formatted_players = [self._format_player(p) for p in room["players"]]

        await self.cm.send_to_socket(socket_id, "room_joined", {
            "roomCode": room_code,
            "mode": room["mode"],
            "settings": room["settings"],
            "players": formatted_players
        })

        await self.cm.broadcast_to_room(room_code, "player_joined", {
            "players": formatted_players
        }, exclude=socket_id)

        # Single-player rooms (e.g. a solo quiz generated from an uploaded
        # document) have nobody to wait for - start as soon as the host joins.
        if is_single:
            await self.start_game(room_code)

    async def toggle_ready(self, socket_id: str, room_code: str):
        """Toggle player ready status"""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]

        for player in room["players"]:
            if player["socket_id"] == socket_id:
                player["is_ready"] = not player["is_ready"]
                break

        formatted_players = [self._format_player(p) for p in room["players"]]

        await self.cm.broadcast_to_room(room_code, "player_ready_changed", {
            "players": formatted_players
        })

        if len(room["players"]) == 2 and all(p["is_ready"] for p in room["players"]):
            await self.start_countdown(room_code)

    async def start_countdown(self, room_code: str):
        """Start the countdown before game begins"""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]
        room["status"] = "countdown"

        await self.cm.broadcast_to_room(room_code, "countdown_started", {"countdown": 3})

        for i in range(3, 0, -1):
            await asyncio.sleep(1)
            if room_code not in self.rooms:
                return
            await self.cm.broadcast_to_room(room_code, "countdown_tick", {"countdown": i - 1})

        await self.start_game(room_code)

    async def start_game(self, room_code: str):
        """Start the actual game"""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]
        room["status"] = "playing"
        room["current_question_index"] = 0
        room["game_ended"] = False

        # Only fetch random questions if room doesn't already have them
        # (AI-powered rooms pre-populate questions via create_room_with_pdf)
        if not room["questions"]:
            count = room["settings"].get("questionsCount", 5)
            room["questions"] = await self.get_random_questions(count)

        if not room["questions"]:
            await self.cm.broadcast_to_room(room_code, "error", {"message": "No questions available"})
            return

        await self.cm.broadcast_to_room(room_code, "game_started", {
            "totalQuestions": len(room["questions"]),
            "timePerQuestion": room["settings"].get("timePerQuestion", 15),
            "sourceDocument": room.get("pdf_filename")
        })

        await asyncio.sleep(0.5)
        await self.send_question(room_code)

    async def send_question(self, room_code: str):
        """Send the current question to all players - SERVER AUTHORITATIVE"""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]

        if room.get("game_ended"):
            return

        idx = room["current_question_index"]

        if idx >= len(room["questions"]):
            await self.end_game(room_code)
            return

        question = room["questions"][idx]
        time_limit = room["settings"].get("timePerQuestion", 15)

        # Reset player answers for this question
        for player in room["players"]:
            player["current_answer"] = None
            player["answer_time"] = None
            player["points_earned"] = 0

        room["question_start_time"] = self.get_server_time()

        await self.cm.broadcast_to_room(room_code, "question", {
            "questionIndex": idx,
            "totalQuestions": len(room["questions"]),
            "question": question["question"],
            "options": question["options"],
            "category": question["category"],
            "timeLimit": time_limit,
            "serverTime": room["question_start_time"]
        })

        # Cancel any existing timer and start new one
        if room_code in self.timers:
            self.timers[room_code].cancel()

        self.timers[room_code] = asyncio.create_task(
            self.question_timer(room_code, time_limit)
        )

    async def question_timer(self, room_code: str, time_limit: int):
        """
        Server-side timer for each question.
        ALWAYS runs to completion — never skipped when players answer early.
        After timer ends, reveals answers and pauses before next question.
        """
        try:
            # Count down every second
            for remaining in range(time_limit, 0, -1):
                await asyncio.sleep(1)

                if room_code not in self.rooms:
                    return

                room = self.rooms[room_code]
                if room.get("game_ended") or room["status"] != "playing":
                    return

                await self.cm.broadcast_to_room(room_code, "time_update", {
                    "timeLeft": remaining - 1
                })

            # ===== TIMER ENDED =====
            # Now reveal correct answers to ALL players at the same time
            await self.reveal_answers(room_code)

            # Pause so players can review the correct answer
            await asyncio.sleep(self.ANSWER_REVIEW_SECONDS)

            # Move to next question
            await self.next_question(room_code)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Timer error for room {room_code}: {e}")

    async def submit_answer(self, socket_id: str, room_code: str, answer: str):
        """
        Handle answer submission.
        Records the answer and score, but does NOT reveal the correct answer.
        The correct answer is only revealed when the timer ends (in reveal_answers).
        """
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]

        if room["status"] != "playing" or room.get("game_ended"):
            return

        idx = room["current_question_index"]
        if idx >= len(room["questions"]):
            return

        question = room["questions"][idx]
        time_limit_ms = room["settings"].get("timePerQuestion", 15) * 1000

        current_time = self.get_server_time()
        question_start = room["question_start_time"]
        time_taken_ms = current_time - question_start

        for player in room["players"]:
            if player["socket_id"] == socket_id:
                # Prevent double-answering
                if player["current_answer"] is not None:
                    return

                # Record answer
                player["current_answer"] = answer
                player["answer_time"] = time_taken_ms
                is_correct = answer == question["correct_answer"]

                # Calculate score
                points_earned = 0
                if is_correct:
                    points_earned = self.calculate_score(time_taken_ms, time_limit_ms)
                    player["score"] += points_earned
                    player["correct_answers"] += 1
                player["points_earned"] = points_earned

                # Tell ONLY this player their answer was accepted (NO correct answer)
                await self.cm.send_to_socket(socket_id, "answer_accepted", {
                    "answer": answer,
                    "timeTaken": round(time_taken_ms / 1000, 2)
                })
                break

    async def reveal_answers(self, room_code: str):
        """
        Called when the timer ends. Reveals the correct answer to ALL players
        at the same time, along with each player's result.
        """
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]
        if room.get("game_ended"):
            return

        idx = room["current_question_index"]
        if idx >= len(room["questions"]):
            return

        question = room["questions"][idx]

        # Send answer_result to EACH player with the correct answer
        for player in room["players"]:
            answered = player["current_answer"] is not None
            is_correct = player["current_answer"] == question["correct_answer"] if answered else False

            player.setdefault("answer_log", []).append({
                "question": question["question"],
                "options": question.get("options", []),
                "correctAnswer": question["correct_answer"],
                "yourAnswer": player["current_answer"],
                "correct": is_correct,
                "pointsEarned": player.get("points_earned", 0) if is_correct else 0
            })

            await self.cm.send_to_socket(player["socket_id"], "answer_result", {
                "correct": is_correct,
                "correctAnswer": question["correct_answer"],
                "yourAnswer": player["current_answer"],
                "score": player["score"],
                "pointsEarned": player.get("points_earned", 0),
                "timedOut": not answered
            })

        # Also broadcast final scores for this question
        formatted_players = [self._format_player(p) for p in room["players"]]
        await self.cm.broadcast_to_room(room_code, "scores_update", {
            "players": formatted_players
        })

    async def next_question(self, room_code: str):
        """Move to the next question or end the game."""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]

        if room.get("game_ended"):
            return

        room["current_question_index"] += 1

        if room["current_question_index"] >= len(room["questions"]):
            await self.end_game(room_code)
        else:
            await self.send_question(room_code)

    async def end_game(self, room_code: str):
        """End the game and show results"""
        if room_code not in self.rooms:
            return

        room = self.rooms[room_code]

        if room.get("game_ended"):
            return

        # Mark game as ended FIRST to prevent re-entry
        room["game_ended"] = True
        room["status"] = "finished"

        print(f"Ending game in room {room_code}")

        # Cancel any active timers - but never the task we're running in.
        # A game that ends naturally reaches here FROM the question timer task
        # (question_timer -> next_question -> end_game); cancelling it would make
        # the next await below raise CancelledError and silently skip saving
        # history and cleaning up the room.
        if room_code in self.timers:
            timer = self.timers.pop(room_code)
            if timer is not asyncio.current_task():
                timer.cancel()

        # Prepare results
        players = room["players"]
        sorted_players = sorted(players, key=lambda p: p["score"], reverse=True)

        winner = None
        if room["mode"] == "multiplayer" and len(sorted_players) >= 2:
            if sorted_players[0]["score"] > sorted_players[1]["score"]:
                winner = sorted_players[0]["username"]
            elif sorted_players[0]["score"] == sorted_players[1]["score"]:
                winner = "draw"

        results = {
            "players": [self._format_player(p) for p in sorted_players],
            "winner": winner,
            "totalQuestions": len(room["questions"]),
            "mode": room["mode"],
            "sourceDocument": room.get("pdf_filename")
        }

        # Send results to EACH connected player
        for player in room["players"]:
            socket_id = player["socket_id"]
            if self.cm.is_connected(socket_id):
                await self.cm.send_to_socket(socket_id, "game_ended", results)
                print(f"Results sent to {player['username']}")

        await asyncio.sleep(0.5)

        # Save game history in background
        spawn(self._save_game_history(room_code, room, winner))

        # Cleanup AI-generated data if applicable
        if room.get("ai_generated"):
            spawn(self._cleanup_ai_data(room_code))

        # Clean up room after delay
        spawn(self._cleanup_room_delayed(room_code))

    async def _save_game_history(self, room_code: str, room: dict, winner: str):
        """Save game history to database"""
        try:
            db = get_database()
            players = room["players"]

            for player in players:
                # Guest user_ids are random UUIDs, not Mongo ObjectIds - they
                # have no account row to write stats to, so skip them here
                # rather than letting one bad ObjectId() call abort the whole
                # loop (which previously also skipped the real player's save).
                if player["user_id"] and ObjectId.is_valid(player["user_id"]):
                    result = "completed"
                    if room["mode"] == "multiplayer":
                        if winner == "draw":
                            result = "draw"
                        elif winner == player["username"]:
                            result = "win"
                        else:
                            result = "loss"

                    opponent = None
                    opponent_score = None
                    if room["mode"] == "multiplayer":
                        for p in players:
                            if p["socket_id"] != player["socket_id"]:
                                opponent = p["username"]
                                opponent_score = p["score"]

                    history = {
                        "user_id": player["user_id"],
                        "room_code": room_code,
                        "mode": room["mode"],
                        "score": player["score"],
                        "total_questions": len(room["questions"]),
                        "correct_answers": player["correct_answers"],
                        "opponent_username": opponent,
                        "opponent_score": opponent_score,
                        "result": result,
                        "source_document": room.get("pdf_filename"),
                        "question_log": player.get("answer_log", []),
                        "played_at": datetime.utcnow()
                    }

                    await db.game_history.insert_one(history)

                    update_data = {
                        "$inc": {
                            "games_played": 1,
                            "total_score": player["score"]
                        }
                    }

                    if result == "win":
                        update_data["$inc"]["games_won"] = 1

                    await db.users.update_one(
                        {"_id": ObjectId(player["user_id"])},
                        update_data
                    )

            print(f"Game history saved for room {room_code}")
        except Exception as e:
            print(f"Error saving game history for room {room_code}: {e}")
            import traceback
            traceback.print_exc()

    async def _cleanup_room_delayed(self, room_code: str):
        """Clean up room after delay"""
        await asyncio.sleep(30)
        if room_code in self.rooms:
            del self.rooms[room_code]
            print(f"Room {room_code} cleaned up")

    async def _cleanup_ai_data(self, room_code: str):
        """Cleanup AI-generated questions and chunks for this room"""
        try:
            import os
            import httpx

            AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{AI_SERVICE_URL}/rooms/{room_code}/cleanup")

                if response.status_code == 200:
                    print(f"AI data cleaned up for room {room_code}")
                else:
                    print(f"Failed to cleanup AI data for room {room_code}: {response.status_code}")

        except Exception as e:
            print(f"Error cleaning up AI data for room {room_code}: {e}")

    async def handle_disconnect(self, socket_id: str):
        """Handle player disconnection"""
        room_code = self.cm.get_room(socket_id)

        if room_code and room_code in self.rooms:
            room = self.rooms[room_code]

            for player in room["players"]:
                if player["socket_id"] == socket_id:
                    player["is_connected"] = False
                    break

            if not room.get("game_ended"):
                formatted_players = [self._format_player(p) for p in room["players"]]
                await self.cm.broadcast_to_room(room_code, "player_disconnected", {
                    "players": formatted_players
                })

            connected = [p for p in room["players"] if p["is_connected"]]
            if len(connected) == 0:
                if not room.get("game_ended"):
                    await self.end_game(room_code)
            elif room["mode"] == "multiplayer" and len(connected) < 2 and room["status"] == "playing":
                if not room.get("game_ended"):
                    await self.end_game(room_code)

        self.cm.disconnect(socket_id)

    def _format_player(self, player: dict) -> dict:
        """Format player data for client"""
        return {
            "socketId": player["socket_id"],
            "username": player["username"],
            "score": player["score"],
            "isReady": player["is_ready"],
            "isConnected": player["is_connected"],
            "correctAnswers": player.get("correct_answers", 0)
        }


connection_manager = ConnectionManager()
game_manager = GameManager(connection_manager)
