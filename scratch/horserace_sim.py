# -*- coding: utf-8 -*-
"""
模擬大學生以「賽馬」為主題使用 AI 研究助理
預期發現問題：冷門主題、跨領域、非典型學術搜尋詞
"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000/api"
SID = f"horserace-sim-{int(time.time())}"

def divider(label=""):
    print("\n" + "=" * 62)
    if label:
        print(f"  {label}")
        print("=" * 62)

def chat(message, step_label=""):
    if step_label:
        print(f"\n--- {step_label} ---")
    print(f"👤 學生：{message}")
    print("-" * 50)
    try:
        r = requests.post(
            f"{BASE}/chat",
            json={"session_id": SID, "message": message},
            timeout=90
        )
        data = r.json()
        t = data.get('type', 'chat')
        content = data.get('content', '')
        papers = data.get('papers', [])
        suggestions = data.get('suggestions', [])

        print(f"🤖 AI [{t}]：")
        # 截短超長輸出
        print(content[:800] + ("..." if len(content) > 800 else ""))

        if papers:
            print(f"\n📄 附帶 papers 資料：{len(papers)} 筆")
            for i, p in enumerate(papers[:3]):
                print(f"   {i+1}. {p.get('title','?')[:70]} ({p.get('year','?')})")
                print(f"      paper_id={p.get('paper_id','')[:20]}  doi={p.get('doi','N/A')}")

        if suggestions:
            print(f"\n💡 建議：")
            for s in suggestions:
                print(f"   • {s}")

        return data
    except Exception as e:
        print(f"❌ API 錯誤：{e}")
        return {}

def get_summaries():
    try:
        r = requests.get(f"{BASE}/summaries/{SID}", timeout=20)
        sums = r.json().get('summaries', [])
        print(f"\n📋 摘要記錄：{len(sums)} 篇")
        for s in sums:
            print(f"   - {s.get('title','?')[:60]}  doi={s.get('doi','N/A')}")
        return sums
    except Exception as e:
        print(f"❌ {e}")
        return []

def get_role_state():
    try:
        r = requests.get(f"{BASE}/role-state/{SID}", timeout=20)
        data = r.json()
        print(f"\n🎯 AI 推導方向：{data.get('description', '未知')}")
        return data
    except Exception as e:
        print(f"❌ {e}")
        return {}

# ─────────────────────────────────────────
divider("賽馬主題壓力測試  Session: " + SID)
print("主題：「用機器學習預測賽馬結果」")
print("預期問題：冷門主題、非典型學術搜尋詞、跨運動/AI 領域")

# Step 1：說明研究方向
r1 = chat(
    "我想做賽馬預測的研究，用 AI 來預測馬匹比賽結果，請幫我找相關論文",
    "Step 1：說明研究方向 + 要求搜尋"
)
time.sleep(2)
get_role_state()
get_summaries()

# Step 2：更精確的英文關鍵字搜尋
r2 = chat(
    "搜尋 horse racing prediction machine learning",
    "Step 2：精確英文搜尋"
)
time.sleep(2)
sums = get_summaries()

# Step 3：換個關鍵字（sport outcome prediction）
r3 = chat(
    "搜尋 sport outcome prediction deep learning",
    "Step 3：換更廣泛的運動預測關鍵字"
)
time.sleep(2)
get_summaries()

# Step 4：試試中文搜尋
r4 = chat(
    "幫我搜尋賽馬結果預測相關文獻",
    "Step 4：中文搜尋（測試翻譯品質）"
)
time.sleep(2)
get_summaries()

# Step 5：嘗試生成矩陣（可能論文不足或不相關）
r5 = chat(
    "生成比較矩陣",
    "Step 5：生成比較矩陣（測試數量是否足夠）"
)
time.sleep(3)

# Step 6：分析研究方向（核心問題測試）
r6 = chat(
    "分析研究方向，幫我找出可行的研究題目",
    "Step 6：分析研究方向（測試 Bug Fix 是否生效）"
)
time.sleep(3)

# 最終狀態報告
divider("模擬完成 — 問題觀察")
get_role_state()
final_sums = get_summaries()

print("\n\n🔎 問題觀察清單：")
print("1. Semantic Scholar 對「horse racing」的學術論文覆蓋率如何？")
print(f"   → 最終收錄論文數：{len(final_sums)} 篇")
print("2. 翻譯功能：中文「賽馬結果預測」是否被正確翻譯為英文搜尋詞？")
print("3. 研究方向推導：AI 是否正確辨識為「AI in Sports / Horse Racing Prediction」？")
print(f"   → Type: {r1.get('type')} / {r6.get('type')}")
print("4. direction intent 是否在 Step 6 被正確觸發？")
print(f"   → Step 6 type = {r6.get('type')} (期望: direction)")
print("5. 論文卡片是否帶有 paper_id 可產生 Semantic Scholar 連結？")
r2_papers = r2.get('papers', [])
if r2_papers:
    pid = r2_papers[0].get('paper_id', '')
    print(f"   → 第一筆 paper_id = '{pid}' (空=無法產生連結)")
else:
    print("   → 無 papers 資料 (搜尋無結果)")
