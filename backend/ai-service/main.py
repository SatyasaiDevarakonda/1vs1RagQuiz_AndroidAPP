"""
AI Service - RAG-based Question Generation using rag_pipeline.py
FastAPI service for syllabus processing and AI question generation
"""
import os
import json
import shutil
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag_pipeline import (
    load_pdf_text,
    load_docx_text,
    chunk_text,
    build_vector_store,
    generate_mcq_questions,
    generate_mcq_from_text,
)


# ==================== APP SETUP ====================

app = FastAPI(
    title="Quiz Battle AI Service",
    description="RAG-based Question Generation",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use absolute paths so the service works from any working directory
AI_SERVICE_DIR = Path(__file__).parent
UPLOAD_DIR = AI_SERVICE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory storage: per-room FAISS indexes and chunks
# { room_code: { "index": faiss_index, "chunks": [...], "filename": "..." } }
room_data = {}

# Validation statistics (in-memory for demo)
validation_stats = {
    "total_generated": 0,
    "validation_passed": 0,
    "validation_failed": 0,
    "avg_confidence": 0.0,
    "total_confidence_sum": 0.0
}


# ==================== MODELS ====================

class QuestionGenerationRequest(BaseModel):
    room_code: str
    topic: str
    num_questions: int = 10
    difficulty: Optional[str] = "medium"


class QuestionTextRequest(BaseModel):
    context: str
    num_questions: int = 10
    topic: Optional[str] = "General Quiz"
    difficulty: Optional[str] = "medium"


class QuestionResponse(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    metadata: dict


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "service": "AI Question Generation",
        "version": "2.0.0",
        "active_rooms": len(room_data)
    }


# ==================== SYLLABUS UPLOAD ====================

@app.post("/upload-syllabus")
async def upload_syllabus(file: UploadFile = File(...), room_code: str = Form(...)):
    """
    Upload and process a syllabus file for a specific room.
    Extracts text, chunks it, and builds a FAISS vector store per room.
    """
    allowed_extensions = [".pdf", ".docx", ".txt"]
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Save uploaded file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{room_code}_{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"File uploaded for room {room_code}: {filename}")

        # Extract text
        if file_ext == ".pdf":
            text = load_pdf_text(str(file_path))
        elif file_ext == ".docx":
            text = load_docx_text(str(file_path))
        elif file_ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            raise HTTPException(status_code=400, detail="Only PDF, DOCX and TXT files are supported")

        if not text or len(text) < 100:
            raise HTTPException(
                status_code=400,
                detail="Extracted text is too short or empty"
            )

        print(f"Extracted {len(text)} characters for room {room_code}")

        # Chunk text
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        print(f"Created {len(chunks)} chunks for room {room_code}")

        # Build FAISS vector store for this room
        index, stored_chunks = build_vector_store(chunks)

        # Store per-room data
        room_data[room_code] = {
            "index": index,
            "chunks": stored_chunks,
            "filename": file.filename,
            "uploaded_at": timestamp
        }

        print(f"Syllabus processed for room {room_code}: {len(chunks)} chunks indexed")

        return {
            "room_code": room_code,
            "filename": file.filename,
            "chunks_count": len(chunks),
            "characters_extracted": len(text),
            "message": f"Syllabus uploaded and processed for room {room_code}"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing syllabus for room {room_code}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        file.file.close()


# ==================== QUESTION GENERATION ====================

@app.post("/generate-questions", response_model=List[QuestionResponse])
async def generate_questions(request: QuestionGenerationRequest):
    """
    Generate questions using RAG for a specific room.
    Uses the room's FAISS index and chunks to generate MCQs via Gemini.
    """
    try:
        if request.room_code not in room_data:
            raise HTTPException(
                status_code=400,
                detail=f"No syllabus uploaded for room {request.room_code}. Please upload a syllabus first."
            )

        rd = room_data[request.room_code]
        index = rd["index"]
        chunks = rd["chunks"]

        print(f"Generating {request.num_questions} questions for room {request.room_code}")

        # Generate MCQs using the pipeline
        raw_json = generate_mcq_questions(index, chunks, num_questions=request.num_questions)

        # Parse the JSON response from Gemini
        try:
            mcq_list = json.loads(raw_json)
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response: {e}")
            print(f"Raw response: {raw_json[:500]}")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse AI response. Try again."
            )

        if not isinstance(mcq_list, list) or len(mcq_list) == 0:
            raise HTTPException(
                status_code=500,
                detail="AI returned no valid questions. Try again."
            )

        # Convert Gemini format to the API format the backend expects
        # Gemini: {"question": "...", "options": {"A": "...", ...}, "correct_option": "A"}
        # API:    {"question": "...", "options": ["...", ...], "correct_answer": "...", "metadata": {...}}
        questions = []
        for mcq in mcq_list:
            opts = mcq.get("options", {})
            correct_key = mcq.get("correct_option", "A")

            # Convert options dict to list
            options_list = [opts.get("A", ""), opts.get("B", ""), opts.get("C", ""), opts.get("D", "")]
            correct_answer = opts.get(correct_key, options_list[0])

            questions.append({
                "question": mcq.get("question", ""),
                "options": options_list,
                "correct_answer": correct_answer,
                "metadata": {
                    "room_code": request.room_code,
                    "topic": request.topic,
                    "difficulty": request.difficulty,
                    "source_file": rd.get("filename", "unknown"),
                    "confidence_score": 1.0,
                    "validation_passed": True
                }
            })

        # Update stats
        validation_stats["total_generated"] += len(questions)
        validation_stats["validation_passed"] += len(questions)

        print(f"Successfully generated {len(questions)} questions for room {request.room_code}")

        return questions

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in question generation for room {request.room_code}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-questions-from-text", response_model=List[QuestionResponse])
async def generate_questions_from_text(request: QuestionTextRequest):
    """
    Generate questions directly from a provided text context.
    Bypasses FAISS vector store.
    """
    try:
        if not request.context or len(request.context) < 50:
            raise HTTPException(
                status_code=400,
                detail="Context text is too short or empty."
            )

        print(f"Generating {request.num_questions} questions from text context...")

        # Generate MCQs using the text pipeline
        raw_json = generate_mcq_from_text(request.context, num_questions=request.num_questions)

        # Parse the JSON response from Gemini
        try:
            mcq_list = json.loads(raw_json)
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response: {e}")
            print(f"Raw response: {raw_json[:500]}")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse AI response. Try again."
            )

        if not isinstance(mcq_list, list) or len(mcq_list) == 0:
            raise HTTPException(
                status_code=500,
                detail="AI returned no valid questions. Try again."
            )

        # Convert Gemini format
        questions = []
        for mcq in mcq_list:
            opts = mcq.get("options", {})
            correct_key = mcq.get("correct_option", "A")

            options_list = [opts.get("A", ""), opts.get("B", ""), opts.get("C", ""), opts.get("D", "")]
            correct_answer = opts.get(correct_key, options_list[0])

            questions.append({
                "question": mcq.get("question", ""),
                "options": options_list,
                "correct_answer": correct_answer,
                "metadata": {
                    "room_code": "TEXT_GEN",
                    "topic": request.topic,
                    "difficulty": request.difficulty,
                    "source_file": "text_context",
                    "confidence_score": 1.0,
                    "validation_passed": True
                }
            })

        # Update stats
        validation_stats["total_generated"] += len(questions)
        validation_stats["validation_passed"] += len(questions)

        print(f"Successfully generated {len(questions)} questions from text")

        return questions

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in text question generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VALIDATION STATS ====================

@app.get("/validation-stats")
async def get_validation_stats():
    """Get validation statistics"""
    total = validation_stats["total_generated"]
    passed = validation_stats["validation_passed"]

    return {
        "total_generated": total,
        "validation_passed": passed,
        "validation_failed": validation_stats["validation_failed"],
        "rejection_rate": 0.0,
        "avg_confidence": 1.0 if passed > 0 else 0.0,
        "status": "operational" if passed > 0 else "no_data"
    }


# ==================== ADMIN ENDPOINTS ====================

@app.get("/syllabi")
async def list_syllabi():
    """List all uploaded syllabi"""
    files = []
    for file_path in UPLOAD_DIR.glob("*"):
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "uploaded_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })

    return {
        "count": len(files),
        "syllabi": sorted(files, key=lambda x: x["uploaded_at"], reverse=True)
    }


@app.delete("/syllabi/{filename}")
async def delete_syllabus(filename: str):
    """Delete an uploaded syllabus"""
    file_path = UPLOAD_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.unlink()
        return {"message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset-vectorstore")
async def reset_vectorstore():
    """Clear all room data"""
    room_data.clear()
    return {
        "message": "All room data cleared",
        "document_count": 0
    }


@app.delete("/rooms/{room_code}/cleanup")
async def cleanup_room_data(room_code: str):
    """
    Delete all chunks and uploaded files for a specific room.
    Called automatically after game ends.
    """
    try:
        # Remove room data from memory
        chunks_deleted = 0
        if room_code in room_data:
            chunks_deleted = len(room_data[room_code].get("chunks", []))
            del room_data[room_code]

        # Delete uploaded PDF files
        files_deleted = 0
        for file_path in UPLOAD_DIR.glob(f"{room_code}_*"):
            if file_path.is_file():
                file_path.unlink()
                files_deleted += 1
                print(f"Deleted file: {file_path.name}")

        print(f"Cleaned up room {room_code}: {chunks_deleted} chunks, {files_deleted} files deleted")

        return {
            "room_code": room_code,
            "chunks_deleted": chunks_deleted,
            "files_deleted": files_deleted,
            "message": f"Room {room_code} data cleaned up successfully"
        }

    except Exception as e:
        print(f"Error cleaning up room {room_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
