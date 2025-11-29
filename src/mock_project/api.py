from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .chatbot import CustomerSupportChatbot

app = FastAPI(title="Customer Support Chatbot API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = CustomerSupportChatbot()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions() -> dict:
    """List all chat sessions with metadata."""
    history_dir = Path("data/chat_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    
    sessions = []
    for file_path in history_dir.glob("*.json"):
        # Skip metadata files
        if file_path.name.endswith("_meta.json"):
            continue
            
        session_id = file_path.stem
        try:
            stat = file_path.stat()
            # Get custom title from metadata
            metadata = _get_session_metadata(session_id)
            custom_title = metadata.get("custom_title")
            
            # Get first message as title if no custom title
            title = custom_title if custom_title else "New Chat"
            if not custom_title:
                from langchain_community.chat_message_histories import FileChatMessageHistory
                chat_history = FileChatMessageHistory(str(file_path))
                messages = chat_history.messages
                if messages:
                    first_msg = messages[0]
                    content = getattr(first_msg, "content", "")
                    if content:
                        title = str(content)[:50] + ("..." if len(str(content)) > 50 else "")
            
            # Count messages
            from langchain_community.chat_message_histories import FileChatMessageHistory
            chat_history = FileChatMessageHistory(str(file_path))
            messages = chat_history.messages
            message_count = len([m for m in messages if hasattr(m, "content")])
            
            sessions.append({
                "id": session_id,
                "title": title,
                "created_at": stat.st_ctime,
                "updated_at": stat.st_mtime,
                "message_count": message_count,
            })
        except Exception:  # noqa: BLE001
            continue
    
    # Sort by updated_at descending (newest first)
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"sessions": sessions}


@app.post("/api/sessions")
def create_session() -> dict:
    """Create a new chat session."""
    import uuid
    session_id = str(uuid.uuid4())
    # Create empty history file
    history_dir = Path("data/chat_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    file_path = history_dir / f"{session_id}.json"
    file_path.write_text("[]", encoding="utf-8")
    # Create metadata file
    meta_path = history_dir / f"{session_id}_meta.json"
    meta_path.write_text(json.dumps({"custom_title": None}), encoding="utf-8")
    return {"session_id": session_id}


def _get_session_metadata(session_id: str) -> dict:
    """Load session metadata (custom title)."""
    history_dir = Path("data/chat_history")
    meta_path = history_dir / f"{session_id}_meta.json"
    if meta_path.exists():
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {"custom_title": None}
    return {"custom_title": None}


def _save_session_metadata(session_id: str, metadata: dict) -> None:
    """Save session metadata."""
    history_dir = Path("data/chat_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    meta_path = history_dir / f"{session_id}_meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    """Delete a chat session and its metadata."""
    history_dir = Path("data/chat_history")
    file_path = history_dir / f"{session_id}.json"
    meta_path = history_dir / f"{session_id}_meta.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        file_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
        return {"status": "deleted"}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


class RenameRequest(BaseModel):
    title: str


@app.put("/api/sessions/{session_id}/rename")
def rename_session(session_id: str, request: RenameRequest) -> dict:
    """Rename a chat session."""
    history_dir = Path("data/chat_history")
    file_path = history_dir / f"{session_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        metadata = _get_session_metadata(session_id)
        metadata["custom_title"] = request.title.strip()[:100]  # Limit to 100 chars
        _save_session_metadata(session_id, metadata)
        return {"status": "renamed", "title": metadata["custom_title"]}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error renaming session: {str(e)}")


@app.get("/api/history/{session_id}")
def get_history(session_id: str) -> dict:
    """Load chat history from saved file."""
    from langchain_community.chat_message_histories import FileChatMessageHistory
    
    history_dir = Path("data/chat_history")
    history_dir.mkdir(parents=True, exist_ok=True)
    file_path = history_dir / f"{session_id}.json"
    
    try:
        chat_history = FileChatMessageHistory(str(file_path))
        messages_list = chat_history.messages
        
        # Convert LangChain messages to frontend format
        messages = []
        for msg in messages_list:
            # LangChain messages have type and content attributes
            msg_type = msg.__class__.__name__
            if "HumanMessage" in msg_type or "Human" in msg_type:
                role = "user"
            elif "AIMessage" in msg_type or "AI" in msg_type or "Assistant" in msg_type:
                role = "assistant"
            else:
                continue  # Skip system messages or unknown types
            
            content = getattr(msg, "content", "")
            if content:
                messages.append({"role": role, "content": str(content)})
        
        return {"messages": messages}
    except Exception as e:  # noqa: BLE001
        # If file doesn't exist or is empty, return empty list
        if not file_path.exists():
            return {"messages": []}
        raise HTTPException(status_code=500, detail=f"Error loading history: {str(e)}")


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    try:
        answer = bot.ask(request.message, session_id=request.session_id)
        return {"answer": answer}
    except Exception as e:  # noqa: BLE001
        import traceback
        error_detail = str(e)
        traceback_str = traceback.format_exc()
        print(f"Error in /api/chat: {error_detail}\n{traceback_str}")
        raise HTTPException(status_code=500, detail=f"Chat error: {error_detail}")


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            question = payload.get("message", "").strip()
            session_id = payload.get("session_id", "default")
            if not question:
                await websocket.send_json({"type": "error", "message": "Câu hỏi trống."})
                continue

            await websocket.send_json({"type": "status", "message": "processing"})
            async for chunk in _stream_answer(question, session_id):
                await websocket.send_json({"type": "token", "token": chunk})
            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()


async def _stream_answer(question: str, session_id: str) -> AsyncIterator[str]:
    async for token in bot.astream(question, session_id=session_id):
        yield token

# --- Serve frontend build (Vite) ---
# Expect built assets under web/dist relative to project root (mock-project)
from pathlib import Path as _Path
_dist_dir = _Path("web/dist").resolve()
if _dist_dir.exists():
    # Mount at root; API remains under /api/*
    app.mount("/", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
else:
    # Minimal placeholder when dist is missing
    @app.get("/")
    def _index_placeholder() -> dict:
        return {"message": "Frontend not built. Run 'npm ci --prefix web && npm run build --prefix web'."}


