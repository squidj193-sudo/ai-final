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


SUMMARY_PROMPT = """你是一位學術研究助理。請根據以下論文內容，以**繁體中文**生成一份結構化摘要。同時，請自動從論文中提取出論文的標題、作者列表與發表年份。

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


class AnalysisSkill:
    """文獻分析 Skill：生成論文結構化摘要"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        from tools.model_helper import FallbackGenerativeModel
        self._model = FallbackGenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.2, max_output_tokens=4096),
        )

    async def summarize(
        self,
        paper_id: str,
        title: Optional[str],
        authors: Optional[list[str]],
        year: Optional[int],
        content: str,
    ) -> PaperSummary:
        """對論文 Markdown 內容進行摘要與元數據提取"""
        import json, asyncio, re, logging
        logger = logging.getLogger("analysis_skill")

        # 若無任何摘要內容，直接回傳基本佔位摘要（避免 Gemini 無法解析）
        if not content or content.strip() in ("", "無摘要"):
            logger.warning(f"No abstract content for paper '{title}', using placeholder summary.")
            return PaperSummary(
                paper_id=paper_id,
                title=title or "未命名論文",
                authors=authors or [],
                year=year,
                research_goal="（原始論文無提供摘要，無法自動分析）",
                methodology="（無資料）",
                main_findings="（無資料）",
                limitations="（無資料）",
                keywords=[],
            )

        prompt = SUMMARY_PROMPT.format(content=content[:8000])  # 截斷避免超出上下文
        try:
            response = await asyncio.to_thread(self._model.generate_content, prompt)
            raw = response.text.strip()
        except Exception as api_e:
            logger.warning(f"Gemini API call failed for '{title}': {api_e}")
            # API 失敗時回傳基本資訊，確保論文不會丟失
            return PaperSummary(
                paper_id=paper_id,
                title=title or "未命名論文",
                authors=authors or [],
                year=year,
                research_goal="（API 呼叫失敗，無法自動分析）",
                methodology="（無資料）",
                main_findings="（無資料）",
                limitations="（無資料）",
                keywords=[],
            )

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
            parsed = json.loads(candidate)
        except Exception as parse_e:
            logger.warning(f"JSON parse failed for '{title}': {parse_e}. Raw: {raw[:200]}")
            # 解析失敗時，至少保留標題與作者等已知資訊
            return PaperSummary(
                paper_id=paper_id,
                title=title or "未命名論文",
                authors=authors or [],
                year=year,
                research_goal="（摘要解析失敗，請嘗試手動上傳 PDF）",
                methodology="（無資料）",
                main_findings="（無資料）",
                limitations="（無資料）",
                keywords=[],
            )
        
        # 決定最終使用的元數據（若使用者有提供則以使用者優先，否則用 AI 提取結果）
        final_title = title if title and title.strip() else parsed.get("title", "未命名論文")
        final_authors = authors if authors and len(authors) > 0 and any(a.strip() for a in authors) else parsed.get("authors", [])
        
        # 確保作者是一個 list[str]
        if isinstance(final_authors, str):
            final_authors = [a.strip() for a in final_authors.split(",") if a.strip()]
        
        final_year = year if year is not None else parsed.get("year")
        if isinstance(final_year, str):
            try:
                final_year = int(final_year)
            except ValueError:
                final_year = None

        # 移除 JSON 中的元數據鍵以避免重複解包
        summary_data = {
            "research_goal": parsed.get("research_goal") or "",
            "methodology": parsed.get("methodology") or "",
            "main_findings": parsed.get("main_findings") or "",
            "limitations": parsed.get("limitations") or "",
            "keywords": parsed.get("keywords") or [],
        }

        return PaperSummary(
            paper_id=paper_id,
            title=final_title,
            authors=final_authors,
            year=final_year,
            **summary_data,
        )

