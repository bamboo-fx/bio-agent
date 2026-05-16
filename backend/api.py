"""FastAPI server for Bio-Brain."""

import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.core import BrainAgent
from knowledge.ingest import ingest_document
from config import DATA_DIR


app = FastAPI(title="Bio-Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = BrainAgent()

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = agent.chat(req.message, req.session_id)
    return ChatResponse(response=result["response"], session_id=result["session_id"])


@app.post("/api/session/{session_id}/end")
async def end_session(session_id: str):
    agent.end_session(session_id)
    return {"status": "ok"}


@app.get("/api/facts")
async def get_facts(limit: int = 50):
    facts = agent.get_facts(limit=limit)
    return {"facts": facts}


@app.post("/api/ingest")
async def ingest_file(file: UploadFile = File(...)):
    # Save uploaded file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingest into knowledge base
    result = ingest_document(str(file_path), agent.memory)
    return result


@app.get("/api/health")
async def health():
    return {"status": "ok", "facts_count": len(agent.get_facts())}
