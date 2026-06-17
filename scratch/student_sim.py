"""
模擬大學生使用 AI 研究助理的完整流程
"""
import requests
import json
import time

BASE = "http://localhost:8000/api"
SID = f"student-sim-{int(time.time())}"

def chat(message):
    print(f"\n👤 學生：{message}")
    print("─" * 60)
    r = requests.post(f"{BASE}/chat", json={"session_id": SID, "message": message}, timeout=90)
    data = r.json()
    print(f"🤖 AI [{data.get('type', 'chat')}]：")
    print(data.get('content', ''))
    if data.get('suggestions'):
        print("\n💡 建議追問：")
        for i, s in enumerate(data.get('suggestions', []), 1):
            print(f"   {i}. {s}")
    return data

def get_summaries():
    r = requests.get(f"{BASE}/summaries/{SID}", timeout=30)
    data = r.json()
    sums = data.get('summaries', [])
    print(f"\n📋 論文摘要記錄：共 {len(sums)} 篇")
    for s in sums:
        print(f"   - {s.get('title', '?')} ({s.get('year', '?')})")
    return sums

def get_role_state():
    r = requests.get(f"{BASE}/role-state/{SID}", timeout=30)
    data = r.json()
    print(f"\n🎯 AI 推導的研究方向：{data.get('description', '未設定')}")
    return data

print("=" * 60)
print("🎓 模擬場景：資工系大四學生，想找 AI 相關論文題目")
print(f"Session ID: {SID}")
print("=" * 60)

# ── 第一輪：完全沒有方向的初始對話 ──
r1 = chat("我是資工系大四學生，對 AI 在醫療方面有點興趣，但不確定要做什麼題目，你可以幫我嗎？")
time.sleep(2)
get_role_state()

# ── 第二輪：更明確指出方向 ──
r2 = chat("我想做醫療影像辨識相關的題目，尤其是 CT 掃描或 X-ray 的自動診斷")
time.sleep(2)
get_role_state()

# ── 第三輪：搜尋論文 ──
r3 = chat("請幫我搜尋 medical image segmentation deep learning 相關的最新論文")
time.sleep(3)
get_summaries()

# ── 第四輪：搜尋更多以建立夠多論文 ──
r4 = chat("再幫我搜尋 chest X-ray AI diagnosis 相關論文")
time.sleep(3)
get_summaries()

# ── 第五輪：產生比較矩陣 ──
r5 = chat("生成比較矩陣")
time.sleep(5)

# ── 第六輪：研究方向分析 ──
r6 = chat("分析研究方向，幫我找出可行的題目")
time.sleep(5)

print("\n" + "=" * 60)
print("✅ 模擬流程完成！")
print("=" * 60)

# 最後角色狀態
get_role_state()
get_summaries()
