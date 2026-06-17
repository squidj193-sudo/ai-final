# -*- coding: utf-8 -*-
import os
import sys
import asyncio
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent / "backend"))

class MockResponse:
    def __init__(self, text):
        self.text = text

class MockModel:
    def __init__(self, response_text):
        self.response_text = response_text
    def generate_content(self, prompt):
        return MockResponse(self.response_text)

async def run_test():
    print("=== [3/6] 執行摘要結構化解析與邊界測試 ===")
    from skills.analysis_skill import AnalysisSkill
    
    # 測試 1：標準且正確的 JSON 格式
    print("1. 測試標準 JSON 格式解析...")
    analysis = AnalysisSkill()
    valid_json = """
    ```json
    {
      "title": "Novel Perovskite Materials",
      "authors": ["Alice Smith", "Bob Jones"],
      "year": 2026,
      "research_goal": "To test perovskite materials.",
      "methodology": "X-ray diffraction.",
      "main_findings": "Stable performance achieved.",
      "limitations": "High cost.",
      "keywords": ["perovskite", "solar"]
    }
    ```
    """
    analysis._model = MockModel(valid_json)
    summary = await analysis.summarize(
        paper_id="test_001",
        title=None,
        authors=None,
        year=None,
        content="Dummy content"
    )
    assert summary.title == "Novel Perovskite Materials"
    assert summary.year == 2026
    assert summary.authors == ["Alice Smith", "Bob Jones"]
    assert summary.research_goal == "To test perovskite materials."
    print("   -> 標準格式解析成功！")

    # 測試 2：部分欄位缺失與異常 JSON (例如缺失 Markdown 標記，或含有空值)
    print("2. 測試欄位缺失與異常格式相容性...")
    dirty_json = """
    這裡是一些雜亂的前言文字。
    {
      "title": "Dirty Paper Title",
      "authors": "Charlie Brown",
      "year": "2024",
      "research_goal": null,
      "methodology": "Laser spectroscopy",
      "main_findings": null,
      "limitations": "",
      "keywords": null
    }
    """
    analysis._model = MockModel(dirty_json)
    summary2 = await analysis.summarize(
        paper_id="test_002",
        title="Override Title",  # 使用者提供的值優先
        authors=["User Author"],
        year=2025,
        content="Dummy content"
    )
    # 驗證使用者提供值優先
    assert summary2.title == "Override Title"
    assert summary2.authors == ["User Author"]
    assert summary2.year == 2025
    # 驗證 null 欄位轉換為預設值
    assert summary2.research_goal == ""
    assert summary2.main_findings == ""
    assert summary2.limitations == ""
    assert summary2.keywords == []
    print("   -> 異常與缺失欄位處理成功！")
    
    print("\n✅ [OK] 摘要結構化解析與邊界測試全部通過！")

if __name__ == "__main__":
    asyncio.run(run_test())
