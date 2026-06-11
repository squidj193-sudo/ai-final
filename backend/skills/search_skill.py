import httpx
from typing import Optional
from pydantic import BaseModel
from pathlib import Path
import json


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

    def __init__(self, api_key: Optional[str] = None, cache_path: str = "./data/search_cache.json"):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key and api_key.strip() else {}
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 查詢結果本機快取
        self._load_cache()
        # Initialize a single persistent client to reuse TCP connection pool
        self.client = httpx.AsyncClient(timeout=15)

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._cache[k] = [PaperResult(**p) for p in v]
            except Exception:
                pass

    def _save_cache(self):
        try:
            data = {}
            for k, v in self._cache.items():
                data[k] = [p.model_dump() for p in v]
            self.cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

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
        
        # 使用字串作為 JSON 快取的鍵
        cache_key = f"{full_query}__limit_{limit}__year_{year_range or 'all'}"
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
        data = None
        last_error = None
        client = self.client
        max_retries = 3  # 適度減少最大重試次數，防止超長延遲
        for attempt in range(max_retries):
            try:
                resp = await client.get(
                    self.SEMANTIC_SCHOLAR_URL, params=params, headers=self.headers
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    import asyncio
                    # Exponential backoff: 1s, 2s, 4s
                    sleep_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                    await asyncio.sleep(sleep_time)
                    continue
            except (httpx.RequestError, Exception) as e:
                last_error = e
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(1 + attempt)
                    continue

        # 若 API 完全超時或回報 429 失敗，嘗試使用 arXiv 備援，若再失敗則回傳本機相似快取
        if data is None:
            arxiv_results = await self.search_arxiv(full_query, limit)
            if arxiv_results:
                self._cache[cache_key] = arxiv_results
                self._save_cache()
                return arxiv_results

            # 尋找包含部分關鍵字的快取 (使用關鍵字重疊度比對)
            query_words = set(full_query.lower().split())
            best_match = None
            max_overlap = 0
            for k, val in self._cache.items():
                k_query = k.split("__limit_")[0].lower()
                k_words = set(k_query.split())
                overlap = len(query_words & k_words)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_match = val
            
            if best_match and max_overlap > 0:
                return best_match

            if last_error:
                if isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 429:
                    raise RuntimeError("學術 API 連線過於頻繁（429 Too Many Requests），請稍候再試。系統已自動套用安全保護。")
                raise last_error
            raise RuntimeError("無法連線至文獻搜尋 API，且無本地快取資料。")

        results = []
        for item in data.get("data", []):
            results.append(
                PaperResult(
                    paper_id=item.get("paperId", "") or "",
                    title=item.get("title", "（無標題）"),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    year=item.get("year"),
                    abstract=item.get("abstract"),
                    url=item.get("url"),
                    doi=item.get("externalIds", {}).get("DOI"),
                )
            )
        self._cache[cache_key] = results
        self._save_cache()
        return results

    async def search_arxiv(self, query: str, limit: int = 10) -> list[PaperResult]:
        """
        當 Semantic Scholar 遇到 429 或超時，使用 arXiv API 進行降級檢索。
        """
        import xml.etree.ElementTree as ET
        import logging
        logger = logging.getLogger("search_skill")
        logger.info(f"Triggering arXiv fallback search for query: '{query}'")
        
        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "max_results": limit
        }
        
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                results = []
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    title_text = title_elem.text.strip().replace('\n', ' ') if title_elem is not None else "（無標題）"
                    
                    id_tag = entry.find('atom:id', ns)
                    arxiv_url = id_tag.text.strip() if id_tag is not None else ""
                    # arXiv ID 格式：arxiv:XXXX.XXXXX，供內部識別用
                    paper_id = "arxiv:" + arxiv_url.split('/abs/')[-1].split('v')[0] if arxiv_url else ""
                    
                    authors = [
                        a.find('atom:name', ns).text.strip() 
                        for a in entry.findall('atom:author', ns) 
                        if a.find('atom:name', ns) is not None
                    ]
                    
                    published = entry.find('atom:published', ns)
                    year = int(published.text[:4]) if published is not None else None
                    
                    summary = entry.find('atom:summary', ns)
                    abstract = summary.text.strip().replace('\n', ' ') if summary is not None else None
                    
                    # url 傳入 arxiv.org 的可點擊連結（前端展示「📖 原文」按鈕用）
                    results.append(PaperResult(
                        paper_id=paper_id,
                        title=title_text,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        url=arxiv_url,  # 直接存 arxiv.org URL
                        doi=None
                    ))
                logger.info(f"arXiv fallback successfully retrieved {len(results)} papers.")
                return results
        except Exception as e:
            logger.warning(f"arXiv fallback search failed: {e}")
        return []

    async def fetch_paper_by_id_or_url(self, query: str) -> Optional[PaperResult]:
        """
        根據 DOI 或 URL 直接向 Semantic Scholar 獲取論文資料。
        """
        import re
        import urllib.parse
        
        # 嘗試提取 DOI
        doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', query)
        
        paper_id = None
        if doi_match:
            paper_id = f"DOI:{doi_match.group(1)}"
        elif query.strip().startswith("http://") or query.strip().startswith("https://"):
            paper_id = f"URL:{query.strip()}"
        
        if not paper_id:
            return None

        # 呼叫 Semantic Scholar Single Paper API
        url = f"https://api.semanticscholar.org/graph/v1/paper/{urllib.parse.quote(paper_id)}"
        params = {
            "fields": "paperId,title,authors,year,abstract,externalIds,url",
        }
        
        client = self.client
        try:
            resp = await client.get(url, params=params, headers=self.headers)
            if resp.status_code == 200:
                item = resp.json()
                return PaperResult(
                    paper_id=item.get("paperId", "") or "",
                    title=item.get("title", "（無標題）"),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    year=item.get("year"),
                    abstract=item.get("abstract"),
                    url=item.get("url"),
                    doi=item.get("externalIds", {}).get("DOI"),
                )
        except Exception as e:
            import logging
            logger = logging.getLogger("search_skill")
            logger.warning(f"Failed to fetch paper by id/url '{paper_id}': {e}")
        return None


