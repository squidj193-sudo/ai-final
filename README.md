# 🔬 AI 研究助理 Agent

一套以 **Gemini 3.5 Flash / Gemma 4 26B** 為核心的學術研究輔助系統，協助研究人員快速完成文獻探索、摘要生成、比較矩陣建立、論文圖譜關聯與研究方向分析。

## 🏗️ 專案結構

```
ai-final/
├── backend/                # Python FastAPI 後端
│   ├── main.py             # API 入口
│   ├── agent_core.py       # Agent Core 協調器
│   ├── skills/             # 技能模組
│   │   ├── state_skill.py      # 角色狀態管理
│   │   ├── search_skill.py     # 論文搜尋
│   │   ├── analysis_skill.py   # 文獻分析
│   │   ├── matrix_skill.py     # 文獻矩陣
│   │   ├── graph_skill.py      # 論文圖譜分析
│   │   └── direction_skill.py  # 研究方向分析
│   ├── tools/
│   │   ├── model_helper.py     # Gemini/Gemma 雙備援切換包裝器
│   │   └── rag.py          # RAG（MarkItDown + 本地 Markdown 檢索）
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Vite + React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx        # 對話搜尋頁
│   │   │   ├── SummaryPage.jsx     # 論文摘要記錄頁
│   │   │   ├── MatrixPage.jsx      # 文獻比較矩陣頁
│   │   │   ├── GraphPage.jsx       # 論文知識圖譜頁
│   │   │   └── DirectionPage.jsx   # 研究方向建議頁
│   │   ├── App.jsx         # 主應用佈局（側邊欄 + 導覽）
│   │   ├── api.js          # API 工具函式
│   │   └── index.css       # 全域樣式
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── 架構/
│   ├── PRD.md              # 產品需求文件
│   ├── ARCHITECTURE.md     # 系統架構說明
│   ├── MODELS.md           # 模型策略
│   ├── KNOWLEDGE_GRAPH.md  # 知識圖譜說明
│   └── IMPLEMENTATION.md   # 技術實作路線圖
└── README.md
```

## 🚀 快速開始

### 1. 後端設定

```bash
cd backend

# 複製環境設定
cp .env.example .env
# 填入你的 GEMINI_API_KEY

# 安裝依賴
pip install -r requirements.txt

# 啟動後端
python main.py
# 後端將在 http://localhost:8000 執行
```

### 2. 前端設定

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
# 前端將在 http://localhost:5173 執行
```

## ✨ 主要功能

| 功能 | 說明 |
|------|------|
| 💬 **對話搜尋** | 輸入關鍵字搜尋學術論文，或上傳 PDF 進行解析 |
| 📋 **論文摘要** | 查看所有已分析論文的結構化摘要（目的/方法/發現/限制）|
| 📊 **比較矩陣** | 自動生成多篇論文的比較表格與研究缺口分析 |
| 🕸️ **論文圖譜** | 基於語意相似度與 PageRank 影響力分析動態建立互動式圖譜 |
| 🧭 **研究方向** | 根據矩陣與圖譜指標識別研究缺口，提出 3-5 個可行研究建議 |

## 🤖 模型策略

系統採用雙模型備援策略：
- **主要模型**：**Gemini 3.5 Flash (gemini-3.5-flash)** 驅動，提供極快且精準的意圖分類、工具調用與對話處理。
- **備援模型**：當 API 流量超限 (429 Rate Limit) 時，自動無感切換至 **Gemma 4 26B (gemma-4-26b-a4b-it)** 以確保系統的高可用性。

請確保在 `backend/.env` 中正確設定 `GEMINI_API_KEY`。

## 📚 文件

- [PRD.md](架構/PRD.md) — 產品需求文件
- [ARCHITECTURE.md](架構/ARCHITECTURE.md) — 系統架構說明
- [MODELS.md](架構/MODELS.md) — 模型策略
- [IMPLEMENTATION.md](架構/IMPLEMENTATION.md) — 技術實作路線圖
- [KNOWLEDGE_GRAPH.md](架構/KNOWLEDGE_GRAPH.md) — 知識圖譜說明
- [DEVELOPER_AGENT_GUIDE.md](DEVELOPER_AGENT_GUIDE.md) — AI Agent 接手開發指南
- [AGENT_WORKFLOWS.md](AGENT_WORKFLOWS.md) — AI Agent 運作與開發工作流

<img width="1918" height="906" alt="image" src="https://github.com/user-attachments/assets/0a26255a-e99c-44f9-b7d3-e5322ad4eb3d" />

<img width="1560" height="642" alt="image" src="https://github.com/user-attachments/assets/1b098ffd-8bc4-4e67-bec1-4e9979966110" />
<img width="707" height="859" alt="image" src="https://github.com/user-attachments/assets/8d71a84d-bc9e-4e51-a2d8-95539aa8e59d" />
<img width="623" height="539" alt="image" src="https://github.com/user-attachments/assets/fad82246-8315-4ffc-92fb-3455b48332e2" />
<img width="636" height="628" alt="image" src="https://github.com/user-attachments/assets/968b8c04-b984-4cfb-872e-6ce43fbeaa84" />
<img width="659" height="801" alt="image" src="https://github.com/user-attachments/assets/31b4d7e7-3f6a-4689-b5db-a2181909dec5" />
<img width="1365" height="712" alt="image" src="https://github.com/user-attachments/assets/06e61a96-db73-4ea9-bc41-bf8b2617480f" />
