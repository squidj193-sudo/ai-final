"""
AI 研究助理 Agent — 文獻矩陣技能
將多篇論文摘要彙整為比較矩陣
"""
import os
import asyncio
import google.generativeai as genai
from .analysis_skill import PaperSummary


MATRIX_PROMPT = """你是一位專注於【{role_context}】領域的學術研究助理。請根據以下多篇論文的結構化摘要，以**繁體中文**生成一份文獻比較矩陣。

使用者的研究背景/主角人設：【{role_context}】

論文資料：
{papers_json}

請以 Markdown 表格格式輸出，欄位包含：論文標題、研究方法、主要發現、研究限制、關鍵字。
並在表格之後，站在【{role_context}】領域的專業視角，另起一段列出與該領域密切相關的「研究缺口分析」，找出這些論文中針對此領域尚未被充分探討的面向（2-5 點）。"""


class MatrixSkill:
    """文獻矩陣 Skill：生成多篇論文的比較矩陣"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=4096),
        )

    async def build_matrix(self, summaries: list[PaperSummary], role_context: str = "") -> str:
        """根據多篇論文摘要生成 Markdown 比較矩陣"""
        import json
        papers_json = json.dumps(
            [s.model_dump() for s in summaries], ensure_ascii=False, indent=2
        )
        prompt = MATRIX_PROMPT.format(
            papers_json=papers_json,
            role_context=role_context or "學術研究"
        )
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        return response.text

