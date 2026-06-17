# -*- coding: utf-8 -*-
import os
import sys
import json
import shutil
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

async def run_test():
    print("=== [1/6] 執行資料相容性測試 ===")
    
    # 建立備份原本 session_data.json 的機制
    orig_path = Path("data/session_data.json")
    backup_path = Path("data/session_data.json.bak")
    if orig_path.exists():
        shutil.copy(orig_path, backup_path)
        print("已備份現有的 session_data.json")
        
    # 建立舊版三層架構的模擬資料
    mock_data = {
        "summaries": {},
        "matrix_cache": {},
        "direction_cache": {},
        "conversations": [],
        "chat_history": {},
        "role_states": {
            "test_session_old_01": {
                "large_direction": "光電物理",
                "medium_direction": "太陽能電池",
                "small_direction": "鈣鈦礦材料"
            },
            "test_session_old_02": {
                "large_direction": "人工智慧",
                "medium_direction": None,
                "small_direction": "物件偵測"
            },
            "test_session_new_01": {
                "research_direction": "大型語言模型微調"
            }
        }
    }
    
    orig_path.parent.mkdir(parents=True, exist_ok=True)
    orig_path.write_text(json.dumps(mock_data, ensure_ascii=False), encoding="utf-8")
    print("已寫入舊版三層架構的模擬資料至 session_data.json")
    
    # 載入 AgentCore 進行移轉
    try:
        from agent_core import AgentCore
        agent = AgentCore()
        
        # 驗證移轉結果
        state1 = agent.state_skill.get_state("test_session_old_01")
        state2 = agent.state_skill.get_state("test_session_old_02")
        state3 = agent.state_skill.get_state("test_session_new_01")
        
        assert state1.research_direction == "光電物理 > 太陽能電池 > 鈣鈦礦材料", f"移轉失敗 1: {state1.research_direction}"
        assert state2.research_direction == "人工智慧 > 物件偵測", f"移轉失敗 2: {state2.research_direction}"
        assert state3.research_direction == "大型語言模型微調", f"移轉失敗 3: {state3.research_direction}"
        
        print("\n✅ [OK] 所有舊版本欄位順利遷移至新版 research_direction！")
        
    except Exception as e:
        print(f"\n❌ [ERROR] 移轉測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        # 還原備份
        if backup_path.exists():
            if orig_path.exists():
                os.remove(orig_path)
            shutil.move(backup_path, orig_path)
            print("已還原原先的 session_data.json")
        elif orig_path.exists():
            os.remove(orig_path)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_test())
