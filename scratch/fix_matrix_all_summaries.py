# -*- coding: utf-8 -*-
import sys

def main():
    filepath = "backend/agent_core.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace under intent == "matrix"
    old_matrix_block = """            elif intent == "matrix":
                summaries_objs = self._summaries.get(session_id, [])
                if len(summaries_objs) < 2:
                    return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
                matrix = await self.matrix_skill.build_matrix(summaries_objs, role_context=full_context)"""

    new_matrix_block = """            elif intent == "matrix":
                summaries_objs = []
                seen = set()
                for sums in self._summaries.values():
                    for s in sums:
                        if s.title.lower() not in seen:
                            seen.add(s.title.lower())
                            summaries_objs.append(s)
                if len(summaries_objs) < 2:
                    return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}
                matrix = await self.matrix_skill.build_matrix(summaries_objs, role_context=full_context)"""

    if old_matrix_block not in content:
        print("Error: old_matrix_block not found in content")
        sys.exit(1)

    content = content.replace(old_matrix_block, new_matrix_block)

    # 2. Replace under intent == "direction"
    old_direction_block = """            elif intent == "direction":
                matrix = self._matrix_cache.get(session_id)
                if not matrix:
                    summaries_objs = self._summaries.get(session_id, [])
                    if len(summaries_objs) >= 2:
                        matrix = await self.matrix_skill.build_matrix(summaries_objs, role_context=full_context)
                        self._matrix_cache[session_id] = matrix
                        self._save_session_data()
                    else:
                        return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}"""

    new_direction_block = """            elif intent == "direction":
                matrix = self._matrix_cache.get(session_id)
                if not matrix:
                    summaries_objs = []
                    seen = set()
                    for sums in self._summaries.values():
                        for s in sums:
                            if s.title.lower() not in seen:
                                seen.add(s.title.lower())
                                summaries_objs.append(s)
                    if len(summaries_objs) >= 2:
                        matrix = await self.matrix_skill.build_matrix(summaries_objs, role_context=full_context)
                        self._matrix_cache[session_id] = matrix
                        self._save_session_data()
                    else:
                        return {"type": "chat", "content": "目前已分析的論文數量不足（至少需要 2 篇），請先上傳或搜尋論文後再生成比較矩陣。"}"""

    if old_direction_block not in content:
        print("Error: old_direction_block not found in content")
        sys.exit(1)

    content = content.replace(old_direction_block, new_direction_block)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print("Successfully patched agent_core.py for all summaries collection")

if __name__ == "__main__":
    main()
