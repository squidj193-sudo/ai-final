"""
AI 研究助理 Agent — 文獻分析技能
負責論文摘要生成與結構化提取
"""
import os
import google.generativeai as genai
from pydantic import BaseModel
from typing import Optional


class PaperSummary(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int]
    research_goal: str       # 研究目的
    methodology: str         # 研究方法
    main_findings: str       # 主要發現
    limitations: str         # 研究限制
    keywords: list[str]      # 關鍵字


SUMMARY_PROMPT = """你是一位學術研究助理。請根據以下論文內容，以**繁體中文**生成一份結構化摘要。

論文內容：
{content}

請嚴格依照以下 JSON 格式回覆，不要加入其他文字：
{{
  "research_goal": "研究目的（1-2 句）",
  "methodology": "研究方法（1-2 句）",
  "main_findings": "主要發現（2-3 句）",
  "limitations": "研究限制（1-2 句）",
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]
}}"""


class AnalysisSkill:
    """文獻分析 Skill：生成論文結構化摘要"""

    MODEL_NAME = "gemini-2.5-flash"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=4096),
        )

    async def summarize(
        self,
        paper_id: str,
        title: str,
        authors: list[str],
        year: Optional[int],
        content: str,
    ) -> PaperSummary:
        """對論文 Markdown 內容進行摘要"""
        import json, asyncio

        prompt = SUMMARY_PROMPT.format(content=content[:8000])  # 截斷避免超出上下文
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        raw = response.text.strip()

        # 移除 markdown 程式碼區塊（如有）
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])

        parsed = json.loads(raw)
        return PaperSummary(
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=year,
            **parsed,
        )
