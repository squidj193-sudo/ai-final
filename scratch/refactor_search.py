# -*- coding: utf-8 -*-
from pathlib import Path

file_path = Path("backend/skills/search_skill.py")
content = file_path.read_text(encoding="utf-8")

# 1. Initialize persistent client in __init__
old_init = """    def __init__(self, api_key: Optional[str] = None, cache_path: str = "./data/search_cache.json"):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key and api_key.strip() else {}
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 查詢結果本機快取
        self._load_cache()"""

new_init = """    def __init__(self, api_key: Optional[str] = None, cache_path: str = "./data/search_cache.json"):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key} if api_key and api_key.strip() else {}
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache = {}  # 查詢結果本機快取
        self._load_cache()
        # Initialize a single persistent client to reuse TCP connection pool
        self.client = httpx.AsyncClient(timeout=15)"""

content = content.replace(old_init, new_init)

# 2. Modify search method
old_search_block = """        import random
        data = None
        last_error = None
        async with httpx.AsyncClient(timeout=15) as client:
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
                        continue"""

new_search_block = """        import random
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
                    continue"""

content = content.replace(old_search_block, new_search_block)

# 3. Modify fetch_paper_by_id_or_url method
old_fetch_block = """        async with httpx.AsyncClient(timeout=15) as client:
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
                logger.warning(f"Failed to fetch paper by id/url '{paper_id}': {e}")"""

new_fetch_block = """        client = self.client
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
            logger.warning(f"Failed to fetch paper by id/url '{paper_id}': {e}")"""

content = content.replace(old_fetch_block, new_fetch_block)

file_path.write_text(content, encoding="utf-8")
print("SearchSkill refactored successfully.")
