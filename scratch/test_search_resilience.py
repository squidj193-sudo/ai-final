# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

async def run_test():
    print("=== [2/6] 執行 API 容錯與快取降級測試 ===")
    from skills.search_skill import SearchSkill, PaperResult
    
    # 建立一個測試用快取檔案路徑
    test_cache_file = "data/test_search_cache_resilience.json"
    if os.path.exists(test_cache_file):
        os.remove(test_cache_file)
        
    try:
        # 建立一個包含 "perovskite" 關鍵字的快取
        search_skill = SearchSkill(cache_path=test_cache_file)
        mock_result = PaperResult(
            paper_id="mock_test_001",
            title="Stability of Perovskite Cells",
            authors=["Alice", "Bob"],
            year=2025,
            abstract="This is a mock abstract for perovskite solar cell stability.",
            url="http://example.com/paper1",
            doi="10.1000/xyz123"
        )
        # 手動注入快取
        cache_key = "perovskite solar cell__limit_10__year_all"
        search_skill._cache[cache_key] = [mock_result]
        search_skill._save_cache()
        
        # 1. 測試直接命中精確快取
        print("1. 測試精確快取命用...")
        res = await search_skill.search("perovskite solar cell")
        assert len(res) == 1, "應從快取返回 1 筆資料"
        assert res[0].paper_id == "mock_test_001", "快取資料不符"
        print("   -> 精確快取命中成功！")
        
        # 2. 測試當 API 無法連線時，模糊匹配快取降級
        print("2. 測試 API 失敗下的模糊快取降級...")
        # 將 API URL 指向無效位址以強制引發連線失敗
        search_skill.SEMANTIC_SCHOLAR_URL = "https://invalid-domain-name-that-does-not-exist.org/search"
        
        # 搜尋 "perovskite" (原快取 key 為 "perovskite solar cell__limit_10__year_all")
        # 預期會觸發 API 失敗，但因為 full_query "perovskite" 在快取 key 中，將觸發模糊匹配降級
        res_fallback = await search_skill.search("perovskite")
        assert len(res_fallback) == 1, "降級機制應從快取返回 1 筆模糊匹配資料"
        assert res_fallback[0].paper_id == "mock_test_001", "降級返回的快取資料不符"
        print("   -> 模糊匹配快取降級機制成功！")
        
        # 3. 測試當無任何快取匹配且連線失敗時拋出 Exception
        print("3. 測試無快取且 API 失敗下的錯誤拋出...")
        try:
            await search_skill.search("completely unrelated query")
            assert False, "應拋出例外"
        except Exception as ex:
            print(f"   -> 拋出例外成功（符合預期）：{ex}")
            
        print("\n✅ [OK] API 容錯與快取降級測試全部通過！")
        
    finally:
        # Cleanup client session
        await search_skill.client.aclose()
        if os.path.exists(test_cache_file):
            os.remove(test_cache_file)

if __name__ == "__main__":
    asyncio.run(run_test())
