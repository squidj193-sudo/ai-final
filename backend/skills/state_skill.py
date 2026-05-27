"""
AI 研究助理 Agent — 角色狀態技能
負責管理使用者的研究方向階層（大方向 / 中方向 / 小方向）
"""
from typing import Optional
from pydantic import BaseModel


class RoleState(BaseModel):
    large_direction: Optional[str] = None   # 大方向，例如：光電
    medium_direction: Optional[str] = None  # 中方向，例如：太陽能電池
    small_direction: Optional[str] = None   # 小方向，例如：鈣鈦礦

    def is_empty(self) -> bool:
        return not any([self.large_direction, self.medium_direction, self.small_direction])

    def get_search_context(self) -> str:
        """回傳搜尋時使用的上下文字串（優先返回最細緻的方向）"""
        if self.small_direction:
            return self.small_direction
        elif self.medium_direction:
            return self.medium_direction
        elif self.large_direction:
            return self.large_direction
        return ""

    def get_full_hierarchy_desc(self) -> str:
        """回傳完整的研究方向層級描述"""
        parts = []
        if self.large_direction:
            parts.append(self.large_direction)
        if self.medium_direction:
            parts.append(self.medium_direction)
        if self.small_direction:
            parts.append(self.small_direction)
        return " > ".join(parts) if parts else "未設定"

    def get_level(self) -> str:
        if self.small_direction:
            return "小方向"
        elif self.medium_direction:
            return "中方向"
        elif self.large_direction:
            return "大方向"
        return "未設定"


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
        level = state.get_level()
        return f"目前研究方向（{level}）：{ctx}"
