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
    return {"status": "ok", "model": "gemini-2.5-flash"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        result = await agent.chat(req.session_id, req.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-paper")
async def upload_paper(
    session_id: str = Form(...),
    title: str = Form(...),
    authors: str = Form(...),   # 以逗號分隔的作者列表
    year: str = Form(None),
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
        author_list = [a.strip() for a in authors.split(",") if a.strip()]
        result = await agent.upload_paper(
            session_id=session_id,
            file_path=tmp_path,
            title=title,
            authors=author_list,
            year=int(year) if year else None,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/summaries/{session_id}")
def get_summaries(session_id: str):
    return {"summaries": agent.get_summaries(session_id)}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
