# -*- coding: utf-8 -*-
import os
import sys
import google.generativeai as genai

# Force UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env variables
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / "backend" / ".env")

api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("正在獲取當前 API Key 可用的 Gemini 模型列表...")
try:
    models = genai.list_models()
    for m in models:
        print(f"- 名稱: {m.name}")
        print(f"  支持的方法: {m.supported_generation_methods}")
        print(f"  描述: {m.description}\n")
except Exception as e:
    print(f"獲取模型列表失敗: {e}")
