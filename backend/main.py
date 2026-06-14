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
    research_direction: str | None = None


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
        research_direction=req.research_direction,
    )
    return {"state": state}


@app.get("/api/role-state/{session_id}")
async def get_role_state(session_id: str):
    state = agent.state_skill.get_state(session_id)
    # 如果狀態全空，但是有已存在的摘要，則在背景自動推導填滿方向！
    if state.is_empty():
        summaries = agent.get_summaries(session_id)
        if summaries:
            import asyncio
            first_sum = summaries[0]
            # 由於 summaries 是以 dict 結構儲存於快取
            title = first_sum.get("title", "")
            keywords = first_sum.get("keywords", [])
            goal = first_sum.get("research_goal", "")
            findings = first_sum.get("main_findings", "")
            
            asyncio.create_task(agent._infer_and_update_direction(
                session_id,
                title,
                keywords,
                f"{goal} {findings}"
            ))
            
    desc = agent.state_skill.describe_state(session_id)
    return {"state": state.model_dump(), "description": desc}


@app.get("/api/graph/{session_id}")
def get_graph(session_id: str):
    from skills.graph_skill import SessionGraphSkill
    summaries = agent.get_summaries(session_id)
    skill = SessionGraphSkill()
    data = skill.get_graph_data(summaries)
    return data


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


class ImportDemosRequest(BaseModel):
    session_id: str


@app.post("/api/system/reset")
def reset_system():
    try:
        res = agent.reset_system_data()
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/import-demos")
async def import_demos(req: ImportDemosRequest):
    try:
        res = await agent.import_demo_papers(req.session_id)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/diagnose")
async def diagnose_system():
    try:
        res = await agent.system_skill.run_diagnostics()
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import Response

@app.get("/api/system/backup")
def download_backup():
    try:
        zip_data = agent.system_skill.create_backup()
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=ai_assistant_backup.zip"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/restore")
async def restore_backup(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="僅能上傳 ZIP 格式的備份檔案")
    try:
        zip_bytes = await file.read()
        # 1. 先重置記憶體與現有資料
        agent.reset_system_data()
        # 2. 還原檔案
        agent.system_skill.restore_backup(zip_bytes)
        # 3. 重新加載資料到 agent 快取中
        agent._load_session_data()
        return {"status": "ok"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class SaveConfigRequest(BaseModel):
    GEMINI_API_KEY: str
    SEMANTIC_SCHOLAR_API_KEY: str
    PAPERS_DB_PATH: str
    GEMINI_MODEL: str


@app.get("/api/system/config")
def get_config():
    try:
        return agent.system_skill.get_env_variables()["masked"]
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/config")
def save_config(req: SaveConfigRequest):
    try:
        agent.system_skill.save_env_variables(req.model_dump())
        agent.reload_config()
        return {"status": "ok"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/rag/documents")
def get_rag_documents():
    try:
        from pathlib import Path
        from tools.rag import RAGStore
        summaries = agent.get_summaries("")
        docs = []
        for s in summaries:
            pid = s["paper_id"]
            title = s["title"]
            year = s["year"]
            
            # 使用 sanitize_paper_id 取得安全檔名
            safe_id = RAGStore.sanitize_paper_id(pid)
            
            # 判斷來源標籤
            pdf_file = Path(agent.rag_store.db_path) / f"{safe_id}.pdf"
            md_file = Path(agent.rag_store.db_path) / f"{safe_id}.md"
            meta_file = Path(agent.rag_store.db_path) / f"{safe_id}.json"
            
            if pdf_file.exists():
                # 使用者上傳的 PDF
                try:
                    size_bytes = pdf_file.stat().st_size
                    size_str = f"{size_bytes / 1024:.1f} KB"
                except Exception:
                    size_str = "未知大小"
            elif md_file.exists():
                # 從搜尋或其他方式寫入 RAG 的論文
                source = "搜尋結果"
                try:
                    if meta_file.exists():
                        import json
                        meta = json.loads(meta_file.read_text(encoding="utf-8"))
                        src = meta.get("source", "")
                        if src == "demo":
                            source = "內建 Demo"
                        elif src == "upload":
                            source = "手動上傳"
                        elif src == "search":
                            source = "搜尋結果"
                except Exception:
                    pass
                size_str = source
            else:
                # 只有記憶體快取，尚未寫入 RAG 索引
                size_str = "未索引"
                    
            docs.append({
                "paper_id": pid,
                "title": title,
                "year": year,
                "size": size_str
            })
        return {"documents": docs}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/system/rag/documents/{paper_id}")
def delete_rag_document(paper_id: str):
    try:
        res = agent.delete_paper(paper_id)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/system/rag/rebuild")
async def rebuild_rag_index():
    try:
        res = await agent.system_skill.rebuild_rag_index(agent.rag_store, agent)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    # Trigger hot-reload to apply FallbackGenerativeModel changes
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

