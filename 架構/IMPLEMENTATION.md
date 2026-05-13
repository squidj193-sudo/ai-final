# 技術實作路線圖：AI 研究助理 Agent

本文件提供 AI 研究助理 Agent 的逐步建置指南，從基礎架構到完整的 AI 智能功能。

## 第一階段：基礎架構與狀態管理（第 1 週）
- **目標**：建立專案結構與基本 Agent 互動。
- **任務**：
    1. 初始化專案目錄與 Git 儲存庫。
    2. 使用 LangGraph 或自定義狀態機實作 `Agent Core` 協調器。
    3. 實作 `角色狀態 Skill`，管理使用者方向（大 / 中 / 小方向）。
    4. 建立基礎對話 CLI 或 Web UI 外殼。

## 第二階段：知識庫與 RAG 管道（第 1-2 週）
- **目標**：讓 Agent 能夠「閱讀」並「記住」研究論文。
- **任務**：
    1. 整合 **MarkItDown** 進行高保真度的 PDF 轉 Markdown。
    2. 設定 **ChromaDB** 作為本地向量儲存。
    3. 實作 `parse_paper` 與 `summarize_paper` 工具。
    4. 使用範例論文驗證 RAG 檢索準確性。

## 第三階段：核心研究技能（第 2-3 週）
- **目標**：實作主要的研究輔助功能。
- **任務**：
    1. 使用 Semantic Scholar 或 arXiv API 實作`論文搜尋 Skill`。
    2. 開發`文獻矩陣 Skill`，將摘要彙整為比較表格。
    3. 建立顯示摘要卡片與比較矩陣的 UI 元件。

## 第四階段：進階智能（第 3-4 週）
- **目標**：讓 Agent 能提供策略性的研究洞察。
- **任務**：
    1. 實作`方向分析 Skill`，偵測比較矩陣中的研究缺口。
    2. 針對 `gemini-2.5-flash` 精煉 Prompt Engineering，生成高品質的研究建議。
    3. 實作報告生成與匯出（Markdown）功能。

## 第五階段：精煉與部署（第 4 週以後）
- **目標**：完善使用者體驗並確保系統穩定性。
- **任務**：
    1. 邀請博士生 / 碩士生進行使用者測試。
    2. 優化回應延遲與 Token 用量。
    3. 完成文件撰寫（README、使用者指南）。
    4. 為期末 Demo 做準備（情境 1-4）。

## 主要依賴套件
- **LLM SDK**：`google-generativeai`（用於 Gemini 2.5 Flash）。
- **PDF 解析**：`markitdown`。
- **向量資料庫**：`chromadb`。
- **Web 框架**：Vite + React（前端）、FastAPI（後端）。
- **狀態管理**：LangGraph / 自定義 Python 邏輯。

## 程式碼範例：技能介面模式（Python）
```python
class BaseSkill:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model = model_name

    async def execute(self, task_input: dict) -> dict:
        raise NotImplementedError

class SearchSkill(BaseSkill):
    async def execute(self, query: str, context: dict) -> list:
        # 1. 使用 gemini-2.5-flash 提取關鍵字
        # 2. 呼叫學術 API
        # 3. 格式化並回傳結果
        pass
```
