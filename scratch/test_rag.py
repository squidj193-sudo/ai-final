import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/.env")))

from tools.rag import RAGStore

try:
    print("Loading RAGStore...")
    store = RAGStore(db_path="../backend/data/chroma")
    print("Collection loaded/created successfully.")
    
    # Try querying
    print("Testing query...")
    res = store.query("test query", n_results=1)
    print("Query result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
