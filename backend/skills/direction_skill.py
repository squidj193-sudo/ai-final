"""
AI 研究助理 Agent — 方向分析技能
根據文獻矩陣識別研究缺口並提出可行的研究方向
"""
import os
import asyncio
import google.generativeai as genai


DIRECTION_PROMPT = """你是一位資深學術研究顧問。請根據以下文獻比較矩陣，以**繁體中文**進行深度分析。

文獻矩陣：
{matrix_content}

使用者的研究背景：{role_context}

請完成以下任務：
1. **領域大方向概覽**：列出此領域目前的 3-5 個主要研究方向。
2. **研究缺口識別**：從矩陣中找出 3-5 個尚未被充分探索的研究缺口。
3. **可行研究建議**：針對每個缺口提出一個具體可行的研究題目，包含：
   - 研究題目
   - 建議方法
   - 預期貢獻
   - 可行性評估（高 / 中 / 低）

請以結構清晰的 Markdown 格式輸出。"""


class DirectionSkill:
    """方向分析 Skill：從文獻矩陣中挖掘研究方向"""

    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemma-4-26b-a4b-it")

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=4096),
        )

    async def analyze(self, matrix_content: str, role_context: str = "") -> str:
        """根據矩陣內容生成研究方向建議報告"""
        prompt = DIRECTION_PROMPT.format(
            matrix_content=matrix_content,
            role_context=role_context or "尚未設定",
        )
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        return response.text
