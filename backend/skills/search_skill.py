"""
AI 研究助理 Agent — 論文搜尋技能
透過 Semantic Scholar API 搜尋學術論文
"""
import httpx
from typing import Optional
from pydantic import BaseModel


class PaperResult(BaseModel):
    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int]
    abstract: Optional[str]
    url: Optional[str]
    doi: Optional[str]


class SearchSkill:
    """論文搜尋 Skill：串接學術 API 搜尋論文"""

    SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key and api_key.strip() else {}
        self._cache = {}  # 查詢結果快取，避免觸發 429 限制

    async def search(
        self,
        query: str,
        context: str = "",
        limit: int = 10,
        year_range: Optional[str] = None,
    ) -> list[PaperResult]:
        """
        搜尋論文。
        :param query: 使用者輸入的關鍵字
        :param context: 角色狀態上下文（例如：光電 > 太陽能電池）
        :param limit: 回傳論文數量上限
        :param year_range: 年份範圍，例如 "2020-2024"
        """
        # 去除重複的關鍵字
        query_words = query.split()
        context_words = context.split() if context else []
        combined_words = []
        for word in context_words + query_words:
            if word not in combined_words:
                combined_words.append(word)
        full_query = " ".join(combined_words)
        cache_key = (full_query, limit, year_range)
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = {
            "query": full_query,
            "limit": limit,
            "fields": "paperId,title,authors,year,abstract,externalIds,url",
        }
        if year_range:
            params["year"] = year_range

        import random
        async with httpx.AsyncClient(timeout=20) as client:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    resp = await client.get(
                        self.SEMANTIC_SCHOLAR_URL, params=params, headers=self.headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        import asyncio
                        # Exponential backoff with jitter: 2, 4, 8, 16 seconds + random jitter
                        sleep_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(sleep_time)
                        continue
                    raise e
                except (httpx.RequestError, Exception) as e:
                    if attempt < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(1 + attempt)
                        continue
                    raise e

        results = []
        for item in data.get("data", []):
            results.append(
                PaperResult(
                    paper_id=item.get("paperId", ""),
                    title=item.get("title", "（無標題）"),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    year=item.get("year"),
                    abstract=item.get("abstract"),
                    url=item.get("url"),
                    doi=item.get("externalIds", {}).get("DOI"),
                )
            )
        self._cache[cache_key] = results
        return results
