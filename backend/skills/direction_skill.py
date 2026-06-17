"""
AI 研究助理 Agent — 方向分析技能
根據文獻矩陣識別研究缺口並提出可行的研究方向
"""
import os
import asyncio
import google.generativeai as genai


DIRECTION_PROMPT = """你是一位資深學術研究顧問。請根據以下文獻比較矩陣與文獻知識圖譜分析指標，以**繁體中文**進行深度分析。

文獻比較矩陣：
{matrix_content}

文獻知識圖譜分析指標（包含重要文獻排名與流派社群分組）：
{graph_insights}

使用者的研究背景：{role_context}

請完成以下任務：
1. **領域大方向概覽**：結合矩陣內容與圖譜社群分群，列出此領域目前的 3-5 個主要研究流派或方向。
2. **研究缺口識別**：分析圖譜中連線稀疏處、孤立社群或低橋接度文獻，找出 3-5 個尚未被充分探索的研究缺口。
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
        from tools.model_helper import FallbackGenerativeModel
        self._model = FallbackGenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=4096),
        )

    async def analyze(self, matrix_content: str, role_context: str = "", graph_insights: str = "") -> str:
        """根據矩陣內容與圖譜指標生成建議報告"""
        prompt = DIRECTION_PROMPT.format(
            matrix_content=matrix_content,
            role_context=role_context or "尚未設定",
            graph_insights=graph_insights or "尚無足夠文獻建立圖譜指標。"
        )
        response = await asyncio.to_thread(self._model.generate_content, prompt)
        return response.text
