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
│       └── rag.py             # 本地檢索 (MarkItDown PDF 解析 + 本地 Markdown 儲存與詞頻檢索)
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

### 3. 本地 PDF 解析與 RAG 輕量檢索知識庫
*   **模組位置**：[rag.py](file:///c:/Users/User/Downloads/1/ai-final/backend/tools/rag.py)
*   **流程**：
    1. 上傳的 PDF 透過 `parse_pdf_to_markdown` 調用微軟 `markitdown` 轉為 Markdown 格式純文字。
    2. 將解析結果以 Sliding Window（1500 字，重疊 300 字）切塊並與元數據儲存在本地 `./data/papers/` 中，查詢時使用本地詞頻匹配檢索。

### 4. 結構化摘要與比較
*   **結構化摘要**：[analysis_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/analysis_skill.py) 要求 Gemini 模型以嚴格的 JSON 格式回傳 `PaperSummary`（包含研究目的、研究方法、主要發現、研究限制）。
*   **文獻矩陣與方向建議**：[matrix_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/matrix_skill.py) 和 [direction_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/direction_skill.py) 負責橫向對比文獻，識別研究缺口 (Research Gaps)，並為使用者量身訂做研究提案。

---

## ✅ 已解決問題與實作說明 (對照問題.md)

以下為 [問題.md](file:///c:/Users/User/Downloads/1/ai-final/%E5%95%8F%E9%A1%8C.md) 中列出的五大問題之具體實作與修復方式：

### 1. PDF 上傳遭遇 `MissingDependencyException` (PdfConverter 錯誤)
*   **修復說明**：此為環境依賴缺失。已在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) 捕獲此異常，若偵測到相依性問題，會向前端拋出友善說明引導使用者於虛擬環境中手動執行：
    ```powershell
    pip install markitdown[pdf]
    ```

### 2. Semantic Scholar 搜尋 429 速率限制 (Client error '429')
*   **修復說明**：
    *   在 [search_skill.py](file:///c:/Users/User/Downloads/1/ai-final/backend/skills/search_skill.py) 內實作了本機 JSON 快取（`./data/search_cache.json`）的載入與儲存機制。
    *   當遇到 429 或超時連線失敗時，系統會自動在已快取的資料中模糊搜尋包含部分關鍵字的歷史文獻，作為優雅降級的備用方案。
    *   優化指數退避重試時間（調整為 1s、2s、4s 並加上抖動），兼顧效能與 API 呼叫安全。

### 3. Gemini 403 API Key Leaked / Invalid
*   **修復說明**：已在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) 捕獲 Google Generative AI 的 `Forbidden` (403) 與 `GoogleAPICallError` 異常。若 API Key 失效或被判洩漏，系統會回傳具體的引導提示，指引用戶於 `backend/.env` 進行密鑰更換。

### 4. 對話偏離主題 (AI 迷失人設)
*   **修復說明**：在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) 內的一般對話分支中，調整並加強了對 `SYSTEM_PROMPT` 中研究方向角色上下文（`role_context`）的傳入。保證 LLM 每次產生回應時都具備明確的研究助理角色邊界。

### 5. 仿照 GPT 提供建議對話 (Follow-up Questions)
*   **修復說明**：
    *   **後端**：在 [agent_core.py](file:///c:/Users/User/Downloads/1/ai-final/backend/agent_core.py) 中的 `_generate_suggestions` 函式中，新增由 LLM 分析上下文自動生成 3 個關聯追問問題的邏輯，並透過 API `suggestions` 欄位回傳。
    *   **前端**：修改 [ChatPage.jsx](file:///c:/Users/User/Downloads/1/ai-final/frontend/src/pages/ChatPage.jsx)，取得 `suggestions` 後動態繪製對話框底部的快速建議追問按鈕，點擊後會自動填入並送出。

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

---

## 📝 3. 強制工作進度記錄與交接規範 (Mandatory Logging & Handoff)

為了避免工作進度因中斷或切換 Agent 而遺失，所有接手開發的 Coding Agent **必須**遵守以下交接規範：

1.  **即時更新開發日誌**：每次解決 Bug、更新設定或新增功能後，應立即前往 [開發日誌.md](file:///c:/Users/User/Downloads/1/ai-final/%E9%96%8B%E7%99%BC%E6%97%A5%E8%AA%8C.md) 新增或調整記錄。
2.  **明確列出下一步計畫**：在 [開發日誌.md](file:///c:/Users/User/Downloads/1/ai-final/%E9%96%8B%E7%99%BC%E6%97%A5%E8%AA%8C.md) 的「待辦與下一步」段落中，更新已完成事項，並羅列未完成事項之優先順序，以便下一個 Agent 能立刻接軌。
3.  **嚴格保護約定配置**：例如核心模型指定使用 `gemma-4-26b-a4b-it`。非經使用者明確指示，不得更換 `.env`、`MODELS.md` 中規定的系統模型。若有任何模型更動，必須於開發日誌特別標記原因。

## 🚫 嚴禁變更與架構邊界 (Guaranteed Architectural Rules)

為了防止優化項目在後續的自動測試與反覆修改中被意外還原，接手的 AI Agent **必須嚴格遵守以下系統設計邊界**：

1. **嚴禁改回三層研究方向**：系統已全面精簡為**單一層級的「研究方向」(`research_direction`)**。嚴禁在 `agent_core.py`、`main.py`、`state_skill.py` 或前端頁面中重新引進 `large_direction`、`medium_direction` 或 `small_direction` 等欄位。
2. **保留 Lazy Loading（延遲載入）優化**：所有大型科學計算庫（如 `networkx`、`numpy`、`sklearn` 等）必須保持在 `graph_skill.py` 的**函式內部導入**，禁止將其移至檔案頂端全域導入，以維持極速啟動效能。
3. **保留 Persistent HTTP Client（持久化連線池）**：`SearchSkill` 中必須繼續使用全域持久的 `self.client = httpx.AsyncClient()` 以重用 TCP 連線池，禁止改回每次搜尋時重複 instantiate 的 `async with httpx.AsyncClient()`。
4. **保留 Rule-based Fast Pass（零延遲快速通道）**：意圖偵測函式 `detect_intent` 中必須維持關鍵字優先過濾的快取設計，在匹配到搜尋/矩陣/方向等請求時，直接由本地常規邏輯觸發對應 Skills，不得使其退化為每次皆由 LLM 作出 Function Calling。

