# 🔬 AI 研究助理 Agent (AI Research Assistant)

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5+-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Gemini](https://img.shields.io/badge/Gemini-3.5%20Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Gemma](https://img.shields.io/badge/Gemma-4%2026B-008080?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/gemma)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

一套以 **Gemini 3.5 Flash** 與 **Gemma 4 26B** 備援機制為核心的學術研究輔助系統。本系統專為學術研究人員、碩博士生打造，提供從「文獻檢索」、「PDF 上傳解析與本地 RAG」、「結構化摘要提取」、「多文獻對比矩陣」到「互動式論文圖譜」與「未來研究方向建議」的一站式工作流程，有效解決學術資訊過載與文獻整理繁雜的痛點。

---

## 🏗️ 系統架構說明 (System Architecture)

系統採用前後端分離（Decoupled）架構，後端提供 REST APIs，前端進行響應式與動態圖譜渲染：

```mermaid
graph TD
    subgraph Frontend [React + Vite 前端]
        App[App.jsx 佈局與狀態] --> Chat[ChatPage.jsx 對話與搜尋]
        App --> Summary[SummaryPage.jsx 摘要紀錄]
        App --> Matrix[MatrixPage.jsx 比較矩陣]
        App --> Graph[GraphPage.jsx 論文圖譜]
        App --> Direction[DirectionPage.jsx 方向分析]
    end

    subgraph Backend [FastAPI + Python 後端]
        API[main.py REST API]
        Agent[agent_core.py 協調器]
        
        subgraph Skills [技能模組]
            State[state_skill.py 角色狀態管理]
            Search[search_skill.py Semantic Scholar 搜尋]
            Analysis[analysis_skill.py 摘要提取]
            MatrixS[matrix_skill.py 矩陣生成]
            GraphS[graph_skill.py 圖譜分析]
            DirS[direction_skill.py 研究方向建議]
        end

        subgraph RAG [知識庫與檢索系統]
            MID[MarkItDown 解析器]
            LocalDB[本地 Markdown 儲存庫]
        end
    end

    %% 前後端串接
    Chat <-->|/api/chat <br> /api/upload-paper| API
    Summary <-->|/api/summaries/{session_id}| API
    Matrix <-->|/api/chat - intent: matrix| API
    Graph <-->|/api/graph/{session_id}| API
    Direction <-->|/api/chat - intent: direction| API

    %% 後端內部流程
    API <--> Agent
    Agent <--> State
    Agent <--> Search
    Agent <--> Analysis
    Agent <--> MatrixS
    Agent <--> GraphS
    Agent <--> DirS
    
    %% RAG 流程
    Agent -->|PDF 上傳| MID
    MID -->|Markdown| LocalDB
    Agent <-->|關聯檢索| LocalDB
```

---

## ✨ 核心功能亮點 (Key Features)

| 功能模組 | Emojis | 說明 | 技術實現 |
| :--- | :---: | :--- | :--- |
| **對話與學術搜尋** | 💬 | 輸入關鍵字搜尋文獻，系統會自動結合目前「研究方向」上下文進行精準過濾與查詢。 | Semantic Scholar API + 模糊比對降級快取 |
| **PDF 論文 RAG** | 📄 | 上傳本地 PDF 檔案，系統自動將其轉為 Markdown，切分文本段落並支援本地詞頻檢索。 | Microsoft MarkItDown + Local Storage |
| **結構化論文摘要** | 📋 | 強制模型以嚴格的 JSON 規格提取論文的「研究目的」、「方法」、「發現」與「限制」。 | Gemini JSON Mode / Pydantic validation |
| **多文獻比較矩陣** | 📊 | 橫向對比多篇已分析的文獻，自動生成比較表格與研究缺口分析，支援 **Markdown 與 CSV** 格式導出。 | Matrix Skill + CSV BOM Parser |
| **互動式論文圖譜** | 🕸️ | 計算論文間的語意相似度，動態生成力導向網絡圖。支援 PageRank 節點大小映射與 Louvain 社群分群著色。 | vis-network + NetworkX (Lazy Loaded) |
| **未來研究方向建議** | 🧭 | 基於已選定文獻的缺口分析，針對目前研究背景，給出 3-5 個具備可行性評估的具體研究課題。 | Direction Skill + Context Injection |

---

## 📂 專案目錄結構 (Directory Structure)

```
ai-final/
├── backend/                   # Python FastAPI 後端服務
│   ├── main.py                # FastAPI 應用入口與 API 路由定義
│   ├── agent_core.py          # 核心協調器 (Agent Core)，處理意圖識別與技能分派
│   ├── requirements.txt       # Python 依賴套件
│   ├── pyproject.toml         # 專案套件設定
│   ├── .env.example           # 環境變數範本
│   ├── skills/                # 核心技能模組 (LLM & API)
│   │   ├── state_skill.py     # 研究方向狀態維護 (單一層級 research_direction)
│   │   ├── search_skill.py    # 學術論文檢索 (含 429 退避與 arXiv/本地快取備援)
│   │   ├── analysis_skill.py  # 論文結構化摘要提取 (JSON Schema)
│   │   ├── matrix_skill.py    # 彙整摘要並生成 Markdown 比較表格與缺口分析
│   │   ├── graph_skill.py     # 基於 TF-IDF 與 NetworkX 的論文知識圖譜計算
│   │   └── direction_skill.py # 基於比較結果，提出具體可行研究方向
│   └── tools/
│       ├── model_helper.py    # 雙模型自動備援包裝器
│       └── rag.py             # 輕量 RAG（使用 MarkItDown 解析 PDF 且利用本地 Markdown 檢索）
├── frontend/                  # React + Vite 前端服務
│   ├── index.html             # 前端 HTML 入口
│   ├── package.json           # 前端依賴與腳本
│   ├── vite.config.js         # Vite 開發伺服器與 API Proxy 設定
│   └── src/
│       ├── main.jsx           # React 掛載入口
│       ├── App.jsx            # 主應用外殼 (含側邊欄導覽與全域狀態管理)
│       ├── api.js             # Axios API 請求模組
│       ├── index.css          # 全域 CSS 設計系統 (變數、重置、基礎樣式)
│       └── pages/             # 功能分頁 (對話搜尋、摘要、比較矩陣、論文圖譜、方向分析)
├── 架構/                      # 系統規格與架構文件目錄
│   ├── PRD.md                 # 產品需求文件
│   ├── ARCHITECTURE.md        # 系統架構說明
│   ├── MODELS.md              # 模型策略與 Token 規劃
│   ├── KNOWLEDGE_GRAPH.md     # 知識圖譜詳細設計規格書
│   └── IMPLEMENTATION.md      # 技術實作里程碑與路線圖
├── data/                      # 後端本地資料庫 (自動生成，包含 RAG Markdown 及對話/搜尋快取)
├── start.py                   # 跨平台一鍵啟動/依賴安裝腳本 (Python)
├── start.bat                  # Windows 一鍵啟動批次檔
└── docker-compose.yml         # Docker 容器化部署設定檔
```

---

## 🚀 快速開始 (Getting Started)

請確認本機已安裝 **Python 3.10+** 及 **Node.js 18+**。

### 方案 A：雙擊一鍵啟動 (推薦 💡)

本專案提供了一鍵自動化腳本，會自動偵測環境、為您安裝前後端依賴套件、啟動伺服器並自動打開瀏覽器：

- **Windows 用戶**：雙擊運行根目錄下的 [start.bat](file:///c:/Users/user/Desktop/研究所/我有想法/成功/AI/start.bat)。
- **跨平台命令**：在終端機運行下方指令：
  ```bash
  python start.py
  ```

---

### 方案 B：手動分步啟動

#### 1. 後端設定 (FastAPI)
```bash
# 進入後端目錄
cd backend

# 複製並設定環境變數
cp .env.example .env
# 請編輯 .env 並填入您的 GEMINI_API_KEY

# 建立並啟用虛擬環境
python -m venv venv
# Windows 啟用:
.\venv\Scripts\activate
# macOS/Linux 啟用:
source venv/bin/activate

# 安裝依賴與 PDF 解析套件
pip install -r requirements.txt
pip install markitdown[pdf]

# 啟動後端伺服器
python main.py
# 後端將運行在 http://localhost:8000
```

#### 2. 前端設定 (React + Vite)
```bash
# 進入前端目錄
cd frontend

# 安裝 Node 套件
npm install

# 啟動開發伺服器
npm run dev
# 若在 Windows PowerShell 遇到權限限制 (PSSecurityException)，請使用:
# npm.cmd run dev

# 前端將運行在 http://localhost:5173
```

---

### 方案 C：Docker 容器化部署 🐳

如果您偏好使用 Docker，可以使用 Docker Compose 進行一鍵部署：

```bash
# 確認已在 backend/.env 中設定 GEMINI_API_KEY
# 啟動所有容器服務 (後端 + 前端)
docker-compose up --build

# 啟動後，請造訪前端地址: http://localhost:5173
```

> [!NOTE]
> Docker 映像檔中已預裝有 `markitdown[pdf]` 所需之系統級依賴（`build-essential` 與 `libmagic1`），無須手動配置。

---

## ⚙️ 環境變數配置 (.env)

請在 `backend/.env` 中進行配置：

```env
# 核心 Gemini API 金鑰 (必須)
GEMINI_API_KEY="您的_Gemini_API_Key"

# 備援模型/主模型自訂 (可選)
GEMINI_PRIMARY_MODEL="gemini-3.5-flash"
GEMINI_FALLBACK_MODEL="gemma-4-26b-a4b-it"

# Semantic Scholar API 金鑰 (可選，空白將使用免費層限制)
SEMANTIC_SCHOLAR_API_KEY=""

# RAG 本地文件儲存庫路徑
PAPERS_DB_PATH="./data/papers"
```

---

## 🤖 模型與防禦策略 (LLM & Fallback Strategy)

本系統為確保極高可用性與流暢體驗，採用**雙模型自動無感切換備援**：

1. **主要推理模型**：預設為 **Gemini 3.5 Flash**，負責意圖檢測、對話引導、以及 RAG 的高速推理。
2. **備援模型**：當遭遇主要 API 流量限制 (HTTP 429 Rate Limit) 或配額耗盡時，`model_helper.py` 會自動捕獲異常並**無縫切換**至 **Gemma 4 26B (gemma-4-26b-a4b-it)**。
3. **API Key 失效防護**：如因 403 憑證過期或安全洩漏遭禁用，系統將捕獲該事件並回傳友善警示引導更換 API 金鑰。
4. **學術搜尋降級**：若遭遇 Semantic Scholar 限制，系統將調用 `arXiv API` 進行搜尋備援，或從本地 `search_cache.json` 中進行模糊相似文獻提取。

---

## 🛠️ 開發人員與 AI Agent 指南

如果您是接手本專案的開發人員或 Coding Agent，請注意以下幾點核心規範：

- **開發工作流規範**：請詳細閱讀 [AGENT_WORKFLOWS.md](AGENT_WORKFLOWS.md) 與 [DEVELOPER_AGENT_GUIDE.md](DEVELOPER_AGENT_GUIDE.md)。
- **核心架構限制**：
  1. **研究方向簡化**：系統已全面精簡為**單一層級的「研究方向」(`research_direction`)**。嚴禁引進 `large_direction` 等多層級屬性。
  2. **Lazy Loading 效能優化**：大型計算庫（`networkx`, `sklearn` 等）必須在 [graph_skill.py](file:///c:/Users/user/Desktop/研究所/我有想法/成功/AI/backend/skills/graph_skill.py) 內部延遲導入，嚴禁在檔案頂部引入，以維持極速啟動。
  3. **持久化連線池**：`SearchSkill` 中必須使用持久的 `httpx.AsyncClient()` 連線池，禁止頻繁銷毀與重建。
- **交接日誌**：每次代碼修改後，請務必更新 [開發日誌.md](開發日誌.md) 的對應進度，並在「待辦與下一步」中勾選與更新任務狀態。

---

## 🖼️ 系統界面展示 (System Showcase)

下列為系統實際運行界面截圖：

### 對話與學術搜尋 (Chat & Search)
![Chat Page](https://github.com/user-attachments/assets/0a26255a-e99c-44f9-b7d3-e5322ad4eb3d)

### 論文結構化摘要卡片 (Structured Summary Card)
![Summary Page](https://github.com/user-attachments/assets/1b098ffd-8bc4-4e67-bec1-4e9979966110)

### 比較矩陣與 CSV 匯出 (Matrix Comparison)
![Matrix Page](https://github.com/user-attachments/assets/8d71a84d-bc9e-4e51-a2d8-95539aa8e59d)

### 論文關係網絡圖譜 (Vis-Network Knowledge Graph)
![Graph Page](https://github.com/user-attachments/assets/fad82246-8315-4ffc-92fb-3455b48332e2)
![Graph Inspector](https://github.com/user-attachments/assets/968b8c04-b984-4cfb-872e-6ce43fbeaa84)

### 研究方向可行性報告 (Research Directions)
![Direction Page](https://github.com/user-attachments/assets/31b4d7e7-3f6a-4689-b5db-a2181909dec5)
![Direction Report](https://github.com/user-attachments/assets/06e61a96-db73-4ea9-bc41-bf8b2617480f)
