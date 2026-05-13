# 🔬 AI 研究助理 Agent

一套以 **Gemini 2.5 Flash** 為核心的學術研究輔助系統，協助研究人員快速完成文獻探索、摘要生成、比較矩陣建立與研究方向分析。

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
│   │   └── direction_skill.py  # 研究方向分析
│   ├── tools/
│   │   └── rag.py          # RAG（MarkItDown + ChromaDB）
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Vite + React 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx        # 對話搜尋頁
│   │   │   ├── SummaryPage.jsx     # 論文摘要記錄頁
│   │   │   ├── MatrixPage.jsx      # 文獻比較矩陣頁
│   │   │   └── DirectionPage.jsx   # 研究方向建議頁
│   │   ├── App.jsx         # 主應用佈局（側邊欄 + 導覽）
│   │   ├── api.js          # API 工具函式
│   │   └── index.css       # 全域樣式
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── PRD.md
├── ARCHITECTURE.md
├── MODELS.md
└── IMPLEMENTATION.md
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
| 🧭 **研究方向** | 根據矩陣識別研究缺口，提出 3-5 個可行研究建議 |

## 🤖 模型

所有 AI 推理均由 **Gemini 2.5 Flash** 驅動。請確保在 `.env` 中正確設定 `GEMINI_API_KEY`。

## 📚 文件

- [PRD.md](./PRD.md) — 產品需求文件
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系統架構說明
- [MODELS.md](./MODELS.md) — 模型策略
- [IMPLEMENTATION.md](./IMPLEMENTATION.md) — 技術實作路線圖
