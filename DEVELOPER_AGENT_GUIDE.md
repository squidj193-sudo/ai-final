# 🤖 AI Agent 程式碼接手與開發指南 (Developer Agent Guide)

本指南旨在為所有接手、修改本專案的 AI Coding Agent 提供清晰、快速上手的脈絡說明，以利無縫接軌開發與除錯。

---

## 🗺️ 專案模組與架構導覽

本系統為前後端分離之 AI 學術研究助理。核心邏輯如下：

```
ai-final/
├── backend/                   # Python FastAPI 後端
│   ├── main.py                # REST API 進入點與路由器配置
│   ├── agent_core.py          # 核心 Agent Core (決策協調器)
│   ├── skills/                # 技能模組 (LLM 任務與 API 整合)
│   │   ├── state_skill.py     # 研究方向狀態 (大/中/小方向)
│   │   ├── search_skill.py    # Semantic Scholar 學術搜尋
│   │   ├── analysis_skill.py  # 論文結構化摘要提取 (JSON Schema)
│   │   ├── matrix_skill.py    # 文獻比較矩陣 (Markdown Table)
│   │   └── direction_skill.py # 建議研究課題與可行性評估
│   └── tools/
│       └── rag.py             # 向量檢索 (MarkItDown PDF 解析 + ChromaDB)
└── frontend/                  # React + Vite 前端
    ├── src/
    │   ├── pages/             # 頁面組件 (對話搜尋、摘要、比較矩陣、研究方向)
    │   └── App.jsx            # 主應用 Shell & 狀態儲存
```

---

## ⚙️ 關鍵元件與程式碼路徑

### 1. 意圖判定與協調機制 (LLM Router)
*   **入口點**：[agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) -> `AgentCore.chat`
*   **流程**：
    1. 接收 `session_id` 和 `message`。
    2. 使用 `detect_intent` (Gemini 輕量 Prompt 加上 temperature=0.1) 識別使用者的意圖類型（`set_direction`、`search`、`analyze`、`matrix`、`direction`、`chat`）。
    3. 依據意圖分派至對應的 `Skill` 模組，並回傳格式化後的 JSON 給前端。

### 2. 學術文獻檢索 (Semantic Scholar)
*   **模組位置**：[search_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/search_skill.py)
*   **邏輯**：串接 Semantic Scholar API，且自動拼接使用者的 `RoleState` (研究方向階層) 上下文以縮小搜尋範圍。內含一個 httpx 指數退避 (Exponential Backoff) 的 429 重試迴圈。

### 3. 本地 PDF 解析與 RAG 向量知識庫
*   **模組位置**：[rag.py](file:///c:/Users/User/Downloads/1/ai-final/backend/tools/rag.py)
*   **流程**：
    1. 上傳的 PDF 透過 `parse_pdf_to_markdown` 調用微軟 `markitdown` 轉為 Markdown 格式純文字。
    2. 使用 `models/embedding-001` 作為嵌入模型，將文本以 Sliding Window（1000字，重疊200字）切塊後存入 ChromaDB 本地持久化資料庫 (`./data/chroma`)。

### 4. 結構化摘要與比較
*   **結構化摘要**：[analysis_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/analysis_skill.py) 要求 Gemini 模型以嚴格的 JSON 格式回傳 `PaperSummary`（包含研究目的、研究方法、主要發現、研究限制）。
*   **文獻矩陣與方向建議**：[matrix_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/matrix_skill.py) 和 [direction_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/direction_skill.py) 負責橫向對比文獻，識別研究缺口 (Research Gaps)，並為使用者量身訂做研究提案。

---

## ⚠️ 已知問題與修復指引 (對照問題.md)

接手 Agent 請優先關注 [問題.md](file:///c:/Users/User/Downloads/1/ai-final/%E5%95%8F%E9%A1%8C.md) 的錯誤，以下是其在程式碼中的對照與修改提示：

### 1. PDF 上傳遭遇 `MissingDependencyException` (PdfConverter 錯誤)
*   **發生點**：上傳 PDF 時，於 [rag.py](file:///c:/Users/User/Downloads/1/ai-final/backend/tools/rag.py#L22) 中執行 `parse_pdf_to_markdown` 時發生。
*   **修復方法**：這屬於執行環境依賴問題。需在虛擬環境中執行：
    ```powershell
    pip install markitdown[pdf]
    # 或
    pip install markitdown[all]
    ```

### 2. Semantic Scholar 搜尋 429 速率限制 (Client error '429')
*   **發生點**：[search_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/search_skill.py#L63) 中的 HTTP 請求。
*   **修復方法**：
    *   檢查 `backend/.env` 是否已設定 `SEMANTIC_SCHOLAR_API_KEY`。
    *   若無 API Key，請調整檢索頻率，或是加入更彈性的快取機制 (Caching)。

### 3. Gemini 403 API Key Leaked / Invalid
*   **發生點**：[agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py#L54) 初始化 Google Generative AI。
*   **修復方法**：提示使用者更換 `backend/.env` 中的 `GEMINI_API_KEY`。

### 4. 對話偏離主題 (AI 迷失人設)
*   **問題描述**：在 ChatPage 中進行一般問答時，Agent 未將使用者的研究方向作為首要上下文。
*   **修復建議**：
    *   調整 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py#L18) 中的 `SYSTEM_PROMPT`。
    *   在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py#L235) 一般對話的分支中，確保把 `role_context` 強烈注入到 system instruction 或每一則 message 的 prefix 中，強制約束 LLM 的回答範圍。

### 5. 仿照 GPT 提供建議對話 (Follow-up Questions)
*   **需求**：回覆完成後，於對話卡片下方多渲染 3 個建議後續問題。
*   **修復建議**：
    *   **後端修改**：在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) 的 `chat` 回傳 JSON 中增加一個 `suggestions: list[str]` 欄位，利用 Gemini 產生與當前上下文相關的 3 個追問問題。
    *   **前端修改**：修改 `frontend/src/pages/ChatPage.jsx` 以渲染這些 `suggestions` 按鈕，並於點擊時自動發送該問題。

---

## 🛠️ 開發與驗證步驟

### 1. 後端啟動與測試
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install markitdown[pdf]
python main.py
```
後端 API 會運行在 `http://localhost:8000`，可以使用 `http://localhost:8000/health` 來確認 API 與模型是否就緒。

### 2. 前端啟動
```powershell
cd frontend
npm install
npm run dev
```
前端介面預設會開啟在 `http://localhost:5173`。
