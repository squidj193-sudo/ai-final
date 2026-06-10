"""
AI 研究助理 Agent — FastAPI 主程式
提供 REST API 供前端呼叫
"""
import os
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import logging
import time
from fastapi import Request

# 設定日誌格式與層級
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

from agent_core import AgentCore

agent = AgentCore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI 研究助理 Agent API",
    description="提供論文搜尋、分析、比較矩陣與研究方向建議的 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 請求日誌紀錄中間件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"Method: {request.method} | Path: {request.url.path} | Status: {response.status_code} | Duration: {duration:.4f}s"
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 請求 / 回應 Schema ────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str


class RoleStateRequest(BaseModel):
    session_id: str
    large_direction: str | None = None
    medium_direction: str | None = None
    small_direction: str | None = None


# ─── API 端點 ─────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "model": os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    import traceback
    try:
        result = await agent.chat(req.session_id, req.message)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-paper")
async def upload_paper(
    session_id: str = Form(...),
    title: str | None = Form(None),
    authors: str | None = Form(None),   # 以逗號分隔的作者列表
    year: str | None = Form(None),
    file: UploadFile = File(...),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅支援 PDF 格式的論文檔案。")

    # 暫存上傳的 PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        author_list = [a.strip() for a in authors.split(",") if a.strip()] if authors else []
        result = await agent.upload_paper(
            session_id=session_id,
            file_path=tmp_path,
            title=title,
            authors=author_list,
            year=int(year) if year and year.strip() else None,
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


class MatrixRequest(BaseModel):
    matrix: str


class DirectionRequest(BaseModel):
    direction: str


@app.get("/api/summaries/{session_id}")
def get_summaries(session_id: str):
    return {"summaries": agent.get_summaries(session_id)}


@app.get("/api/matrix/{session_id}")
def get_matrix(session_id: str):
    return {"matrix": agent.get_matrix(session_id)}


@app.post("/api/matrix/{session_id}")
def set_matrix(session_id: str, req: MatrixRequest):
    agent.set_matrix(session_id, req.matrix)
    return {"status": "ok"}


@app.get("/api/direction/{session_id}")
def get_direction(session_id: str):
    return {"direction": agent.get_direction(session_id)}


@app.post("/api/direction/{session_id}")
def set_direction(session_id: str, req: DirectionRequest):
    agent.set_direction(session_id, req.direction)
    return {"status": "ok"}


@app.post("/api/role-state")
def update_role_state(req: RoleStateRequest):
    state = agent.update_role_state(
        req.session_id,
        large_direction=req.large_direction,
        medium_direction=req.medium_direction,
        small_direction=req.small_direction,
    )
    return {"state": state}


@app.get("/api/role-state/{session_id}")
def get_role_state(session_id: str):
    state = agent.state_skill.get_state(session_id)
    desc = agent.state_skill.describe_state(session_id)
    return {"state": state.model_dump(), "description": desc}


@app.get("/api/graph/{session_id}")
def get_graph(session_id: str):
    from skills.graph_skill import SessionGraphSkill
    summaries = agent.get_summaries(session_id)
    skill = SessionGraphSkill()
    html = skill.generate_graph_html(summaries)
    return {"html": html, "count": len(summaries)}


class ConversationsRequest(BaseModel):
    conversations: list[dict]


class ChatHistoryRequest(BaseModel):
    history: list[dict]


@app.get("/api/conversations")
def get_conversations():
    return {"conversations": agent.get_conversations()}


@app.post("/api/conversations")
def set_conversations(req: ConversationsRequest):
    agent.set_conversations(req.conversations)
    return {"status": "ok"}


@app.delete("/api/conversations/{session_id}")
def delete_conversation(session_id: str):
    agent.delete_session(session_id)
    return {"status": "ok"}


@app.get("/api/chat-history/{session_id}")
def get_chat_history(session_id: str):
    return {"history": agent.get_chat_history(session_id)}


@app.post("/api/chat-history/{session_id}")
def set_chat_history(session_id: str, req: ChatHistoryRequest):
    agent.set_chat_history(session_id, req.history)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
