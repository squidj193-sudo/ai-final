"""
AI 研究助理 Agent — 角色狀態技能
負責管理使用者的研究方向階層（大方向 / 中方向 / 小方向）
"""
from typing import Optional
from pydantic import BaseModel


class RoleState(BaseModel):
    research_direction: Optional[str] = None   # 研究方向，例如：鈣鈦礦太陽能電池

    def is_empty(self) -> bool:
        return not self.research_direction

    def get_search_context(self) -> str:
        """回傳搜尋時使用的上下文字串"""
        return self.research_direction or ""

    def get_full_hierarchy_desc(self) -> str:
        """回傳完整的研究方向描述"""
        return self.research_direction or "未設定"

    def get_level(self) -> str:
        return "研究方向" if self.research_direction else "未設定"


class StateSkill:
    """角色狀態 Skill：持久化使用者研究範疇"""

    def __init__(self):
        # 以 session_id 為鍵，儲存每位使用者的角色狀態
        self._states: dict[str, RoleState] = {}

    def get_state(self, session_id: str) -> RoleState:
        return self._states.get(session_id, RoleState())

    def update_state(self, session_id: str, **kwargs) -> RoleState:
        current = self.get_state(session_id)
        updated = current.model_copy(update=kwargs)
        self._states[session_id] = updated
        return updated

    def reset_state(self, session_id: str) -> RoleState:
        self._states[session_id] = RoleState()
        return self._states[session_id]

    def describe_state(self, session_id: str) -> str:
        state = self.get_state(session_id)
        if state.is_empty():
            return "尚未設定研究方向。"
        ctx = state.get_search_context()
        return f"目前研究方向：{ctx}"
