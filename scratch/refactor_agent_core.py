# -*- coding: utf-8 -*-
from pathlib import Path

file_path = Path("backend/agent_core.py")
content = file_path.read_text(encoding="utf-8", errors="replace")

# 1. Update _intent_model configuration
old_config = """        self._intent_model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(temperature=0.1, max_output_tokens=256),
        )"""

new_config = """        self._intent_model = genai.GenerativeModel(
            self.MODEL_NAME,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=32,
                response_mime_type="application/json"
            ),
        )"""

content = content.replace(old_config, new_config)

# 2. Update detect_intent logic to support Rule-based Fast Pass
old_detect = """    async def detect_intent(self, message: str) -> dict:
        prompt = INTENT_PROMPT.format(message=message)
        logger.info(f"Detecting intent for message: {message[:50]}...")"""

new_detect = """    async def detect_intent(self, message: str) -> dict:
        # 1. Rule-based Fast Pass (關鍵字優先過濾，實現零延遲過濾)
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in ["搜尋", "查詢", "找文獻", "找論文", "search"]):
            query = message
            for prefix in ["幫我搜尋", "幫我查詢", "搜尋關於", "查詢關於", "搜尋", "查詢", "search for", "search"]:
                if prefix in query:
                    query = query.split(prefix, 1)[1].strip()
            query = query.strip("的文獻論文、.?!。？！")
            return {"intent": "search", "query": query}
        elif any(kw in msg_lower for kw in ["矩陣", "對比", "比較表格", "matrix"]):
            return {"intent": "matrix", "query": ""}
        elif any(kw in msg_lower for kw in ["方向建議", "研究方向", "研究題目", "可行題目", "課題", "direction"]):
            return {"intent": "direction", "query": ""}

        # 2. Fallback to Gemini
        prompt = INTENT_PROMPT.format(message=message)
        logger.info(f"Detecting intent via LLM for message: {message[:50]}...")"""

content = content.replace(old_detect, new_detect)

file_path.write_text(content, encoding="utf-8")
print("AgentCore refactored successfully.")
