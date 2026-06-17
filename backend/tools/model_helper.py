import os
import logging
import google.generativeai as genai
import google.api_core.exceptions as g_exceptions

logger = logging.getLogger("model_fallback")

class FallbackGenerativeModel:
    """
    模型包裝器：當主要模型（如 gemini-3.5-flash）配額耗盡 (429/ResourceExhausted) 時，
    自動無感切換至備援模型（如 gemma-4-26b-a4b-it）。
    """
    def __init__(self, model_name, **kwargs):
        # 優先讀取 GEMINI_PRIMARY_MODEL，再來是 GEMINI_MODEL，最末 fallback 到 gemini-3.5-flash
        self.primary_name = os.getenv("GEMINI_PRIMARY_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
        
        # 備援模型預設為 gemma-4-26b-a4b-it
        self.fallback_name = os.getenv("GEMINI_FALLBACK_MODEL", "gemma-4-26b-a4b-it")
        
        # 如果傳入的 model_name 是預設的，將其改為 primary_name 進行初次嘗試
        if model_name in ("gemma-4-26b-a4b-it", "gemini-3.1-flash-lite") or not model_name:
            self.model_name = self.primary_name
        else:
            self.model_name = model_name

        self.kwargs = kwargs
        
        logger.info(f"Initializing FallbackGenerativeModel with Primary: '{self.model_name}' and Fallback: '{self.fallback_name}'")
        self.primary_model = genai.GenerativeModel(self.model_name, **kwargs)
        self.fallback_model = genai.GenerativeModel(self.fallback_name, **kwargs)

    def generate_content(self, contents, **kwargs):
        try:
            logger.info(f"Generating content with primary model: '{self.model_name}'")
            return self.primary_model.generate_content(contents, **kwargs)
        except (g_exceptions.ResourceExhausted, g_exceptions.ResourceExhausted) as e:
            logger.warning(f"Primary model '{self.model_name}' ResourceExhausted (429). Falling back to '{self.fallback_name}'. Error: {e}")
            return self.fallback_model.generate_content(contents, **kwargs)
        except Exception as e:
            # 檢查是否為 429 狀態碼
            if hasattr(e, "code") and e.code == 429:
                logger.warning(f"Primary model '{self.model_name}' rate limited (code 429). Falling back to '{self.fallback_name}'. Error: {e}")
                return self.fallback_model.generate_content(contents, **kwargs)
            
            # 若為 403 (金鑰失效) 等其他異常，則不嘗試 fallback 而是直接丟出
            logger.error(f"Error occurred in primary model '{self.model_name}': {e}")
            raise e
