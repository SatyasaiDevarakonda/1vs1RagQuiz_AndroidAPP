"""
RAG Pipeline - PDF processing, chunking, vector store, and question generation
Uses FAISS for vector search and Google Gemini for MCQ generation
"""

import os
import re
import json
import faiss
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from sentence_transformers import SentenceTransformer

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

from google import genai

client = genai.Client(api_key=(os.getenv("GOOGLE_API_KEY") or "").strip())
embedder = SentenceTransformer("all-MiniLM-L6-v2")


def load_pdf_text(pdf_path):
    """Extract text from a PDF file"""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def load_docx_text(docx_path):
    """Extract text from a DOCX file."""
    document = Document(docx_path)
    lines = []
    for para in document.paragraphs:
        text = (para.text or "").strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])

        if end == text_len:
            break

        start = end - overlap

    return chunks


def build_vector_store(chunks):
    """Build a FAISS index from text chunks"""
    embeddings = embedder.encode(chunks).astype("float32")
    dim = embeddings.shape[1]

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    return index, chunks


def retrieve_chunks(query, index, chunks, k=5):
    """Retrieve the most relevant chunks for a query"""
    query_vec = embedder.encode([query]).astype("float32")
    _, indices = index.search(query_vec, k)
    return [chunks[i] for i in indices[0]]


def clean_llm_json(text: str) -> str:
    """Strip markdown code fences from LLM JSON output"""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


def generate_mcq_questions(index, chunks, num_questions=5):
    """Generate MCQ questions using RAG + Gemini"""
    retrieved = retrieve_chunks(
        "Generate questions from this document",
        index,
        chunks,
        k=6
    )

    context = "\n\n".join(retrieved)
    return generate_mcq_from_text(context, num_questions)


def generate_mcq_from_text(context, num_questions=5):
    """Generate MCQ questions directly from text using Gemini"""
    prompt = f"""
You are given content.

Task:
- Generate EXACTLY {num_questions} multiple-choice questions (MCQs)
- Each question must have EXACTLY 4 options (A, B, C, D)
- Only ONE option should be correct
- Questions must be answerable ONLY from the given content
- Mix conceptual and factual questions
- Do NOT use external knowledge

Output format (STRICT JSON):
[
  {{
    "question": "...",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "correct_option": "A"
  }}
]

Content:
{context}

Return ONLY valid JSON. No explanations.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return clean_llm_json(response.text)
