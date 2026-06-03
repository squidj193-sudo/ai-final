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


SUMMARY_PROMPT = """你是一位學術研究助理。請根據以下論文內容，以**繁體中文**生成一份結構化摘要。並請同時自動從論文中提取出論文的標題、作者列表與發表年份。

論文內容：
{content}

請嚴格依照以下 JSON 格式回覆，不要加入其他文字：
{{
  "title": "論文的英文或中文完整標題/名稱",
  "authors": ["第一作者姓名", "第二作者姓名", ...],
  "year": 發表年份（數字，例如 2024；若在論文中完全找不到年份，請填 null）,
  "research_goal": "研究目的（1-2 句）",
  "methodology": "研究方法（1-2 句）",
  "main_findings": "主要發現（2-3 句）",
  "limitations": "研究限制（1-2 句）",
  "keywords": ["關鍵字1", "關鍵字2", "關鍵字3"]
}}"""


METADATA_PROMPT = """你是一位學術研究助理。請從以下論文內容（通常是論文的第一頁或開頭部分）中，提取該論文的：
1. 論文標題 (title)
2. 作者列表 (authors)
3. 發表年份 (year)

論文開頭內容：
{content}

請嚴格依照以下 JSON 格式回覆，只回傳 JSON，不要有其他文字或 Markdown 標籤：
{{
  "title": "提取的論文標題，如果沒有找到，請填寫空字串",
  "authors": ["作者1", "作者2"],
  "year": 2024
}}
注意：
- year 必須是整數年份，如果找不到，請回傳 null 或不包含此欄位。
- authors 必須是字串陣列，如果找不到，請回傳空陣列 []。
- title 請儘量完整且準確地提取，如果找不到，請回傳空字串。
"""


class AnalysisSkill:
    """文獻分析 Skill：生成論文結構化摘要"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=4096),
        )

    async def extract_metadata(self, content: str) -> dict:
        """從論文開頭內容提取 Title, Authors, Year"""
        import json, asyncio, re
        prompt = METADATA_PROMPT.format(content=content[:4000])
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        raw = response.text.strip()

        # 魯棒解析 JSON 內容
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
        else:
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                candidate = raw[start:end+1].strip()
            else:
                candidate = raw.strip()

        try:
            return json.loads(candidate)
        except Exception:
            return {"title": "", "authors": [], "year": None}

    async def summarize(
        self,
        paper_id: str,
        content: str,
    ) -> PaperSummary:
        """對論文 Markdown 內容進行摘要與元數據提取"""
        import json, asyncio, re

        prompt = SUMMARY_PROMPT.format(content=content[:8000])  # 截斷避免超出上下文
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        raw = response.text.strip()

        # 魯棒解析 JSON 內容
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
        else:
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1:
                candidate = raw[start:end+1].strip()
            else:
                candidate = raw.strip()

        parsed = json.loads(candidate)
        
        # 提取並過濾
        title = parsed.get("title", "未命名論文")
        authors = parsed.get("authors", [])
        year = parsed.get("year", None)
        
        summary_data = {k: v for k, v in parsed.items() if k not in ["title", "authors", "year"]}
        
        return PaperSummary(
            paper_id=paper_id,
            title=title,
            authors=authors,
            year=year,
            **summary_data,
        )
