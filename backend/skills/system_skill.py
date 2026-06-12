"""
AI 研究助理 Agent — 系統診斷與演示技能
負責檢驗系統狀態、金鑰可用性、依賴項，以及匯入示範學術論文
"""
import os
import sys
import logging
import asyncio
import httpx
import google.generativeai as genai
import google.api_core.exceptions as g_exceptions
from pathlib import Path

logger = logging.getLogger("system_skill")

class SystemSkill:
    """系統診斷與演示 Skill"""

    async def run_diagnostics(self) -> dict:
        """執行系統全面檢測，回傳檢查項目清單"""
        results = {
            "gemini_api": {"status": "pending", "message": ""},
            "pdf_parser": {"status": "pending", "message": ""},
            "semantic_scholar": {"status": "pending", "message": ""},
            "write_permission": {"status": "pending", "message": ""}
        }

        # 1. 檢測 Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            results["gemini_api"] = {
                "status": "failed",
                "message": "GEMINI_API_KEY 未設定，請至 backend/.env 設定。"
            }
        else:
            try:
                # 測試極小 token 請求
                model_name = os.getenv("GEMINI_PRIMARY_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name)
                # 使用 asyncio.to_thread 避免阻塞
                response = await asyncio.to_thread(
                    model.generate_content,
                    "ping",
                    generation_config={"max_output_tokens": 5}
                )
                if response.text:
                    results["gemini_api"] = {
                        "status": "success",
                        "message": f"連線正常 (模型: {model_name})"
                    }
            except g_exceptions.Forbidden:
                results["gemini_api"] = {
                    "status": "failed",
                    "message": "金鑰遭拒絕 (403)。金鑰可能已失效或被系統判定洩漏，請更換金鑰。"
                }
            except Exception as e:
                results["gemini_api"] = {
                    "status": "warning",
                    "message": f"呼叫 API 發生異常：{str(e)}。請檢查網路連線。"
                }

        # 2. 檢測 PDF 解析器依賴
        try:
            from markitdown import MarkItDown
            results["pdf_parser"] = {
                "status": "success",
                "message": "MarkItDown 已正確安裝"
            }
            # 檢查是否具備讀取 PDF 的能力 (markitdown 是否安裝了 pdfminer.six 依賴)
            # 在 python 裡嘗試載入 pdfminer 檢查是否拋出 ImportError
            try:
                import pdfminer
                results["pdf_parser"]["message"] += " (包含 PDF 解讀能力)"
            except ImportError:
                results["pdf_parser"] = {
                    "status": "warning",
                    "message": "已安裝 markitdown，但缺少 PDF 選填依賴。請執行 `pip install markitdown[pdf]` 以正常讀取 PDF 論文。"
                }
        except ImportError:
            results["pdf_parser"] = {
                "status": "failed",
                "message": "缺少 markitdown 套件。請在後端執行 `pip install markitdown`。"
            }

        # 3. 檢測 Semantic Scholar 連線
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1")
                if resp.status_code == 200:
                    results["semantic_scholar"] = {
                        "status": "success",
                        "message": "學術資料庫 API 連線正常"
                    }
                else:
                    results["semantic_scholar"] = {
                        "status": "warning",
                        "message": f"學術 API 回傳非預期狀態碼 ({resp.status_code})。可能遭遇配額限制。"
                    }
        except Exception as e:
            results["semantic_scholar"] = {
                "status": "warning",
                "message": f"無法連線至學術資料庫：{str(e)}。請檢查您的網路代理或連線。"
            }

        # 4. 檢測磁碟寫入權限
        try:
            test_dir = Path("./data/papers")
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            results["write_permission"] = {
                "status": "success",
                "message": "磁碟資料讀寫權限正常"
            }
        except Exception as e:
            results["write_permission"] = {
                "status": "failed",
                "message": f"無法寫入 data 目錄，磁碟可能唯讀或權限不足：{str(e)}"
            }

        return results

    def get_demo_papers(self) -> list[dict]:
        """獲取內置示範學術論文資料，供一鍵匯入。
        兩篇 Demo 論文均屬同一學術領域（大型語言模型 / NLP），
        以正確示範系統「專注研究方向」的個人化設計理念。
        """
        return [
            {
                "paper_id": "demo_chain_of_thought_2023",
                "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
                "authors": ["Wei, J.", "Wang, A.", "Schuurmans, D."],
                "year": 2023,
                "research_goal": "To investigate whether prompting large language models to generate a sequence of intermediate reasoning steps before answering improves their performance on complex reasoning tasks.",
                "methodology": "Introduced Chain-of-Thought (CoT) prompting and evaluated it on arithmetic, symbolic, and commonsense reasoning benchmarks using PaLM, GPT-3, and LaMDA.",
                "main_findings": "CoT prompting significantly improves reasoning capabilities. PaLM 540B achieved state-of-the-art results on GSM8K math benchmark, outperforming fine-tuned models.",
                "limitations": "CoT prompting only provides substantial benefits for models with 100B or more parameters; small models often generate incorrect reasoning steps.",
                "keywords": ["large language models", "chain of thought", "reasoning", "prompt engineering"],
                "content": (
                    "# Chain-of-Thought Prompting Elicits Reasoning in Large Language Models\n\n"
                    "## Abstract\n"
                    "We explore how generating a chain of thought—a series of intermediate reasoning steps—significantly improves the ability "
                    "of large language models to perform complex reasoning. We show that such reasoning capabilities emerge naturally "
                    "via simple prompt engineering, without the need for parameter fine-tuning or specialized training datasets.\n\n"
                    "## Research Goal\n"
                    "Our research goal is to unlock multi-step reasoning in pretrained language models (LLMs). Traditional prompts force "
                    "direct outputs, which fail on complex math word problems and symbolic deduction. We want to test if intermediate steps bridge this gap.\n\n"
                    "## Methodology\n"
                    "We design Chain-of-Thought prompts by prefixing few-shot exemplars with a 'Q: [Question] -> A: [Thought steps] -> [Final Answer]' format. "
                    "We benchmarked performance across arithmetic (GSM8K, SVAMP), symbolic reasoning (last letter concatenation), and commonsense tasks (StrategyQA).\n\n"
                    "## Main Findings\n"
                    "Results show that CoT prompting outperforms standard prompting across all benchmarks. PaLM 540B achieved a record 58% accuracy on GSM8K, "
                    "outperforming even fine-tuned task-specific neural architectures. It enables models to explain their reasoning, making outputs more interpretable.\n\n"
                    "## Limitations\n"
                    "A critical limitation is that Chain-of-Thought prompting is an emergent property of scale. It only works effectively for models with "
                    "approximately 100 billion parameters or more. Smaller models (e.g., under 10B parameters) produce incorrect chains of thoughts, leading to worse accuracy."
                )
            },
            {
                "paper_id": "demo_rag_2023",
                "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
                "authors": ["Lewis, P.", "Perez, E.", "Piktus, A.", "Petroni, F."],
                "year": 2023,
                "research_goal": "To propose a general-purpose fine-tuning recipe for Retrieval-Augmented Generation (RAG) models that can retrieve relevant documents and use them to generate accurate, knowledge-grounded answers.",
                "methodology": "Combined a dense passage retrieval model (DPR) with a seq2seq generator (BART). The retriever fetches top-k passages from Wikipedia; the generator conditions on both the input query and retrieved passages.",
                "main_findings": "RAG models set the state-of-the-art on multiple open-domain QA benchmarks (Natural Questions, WebQuestions, CuratedTrec) and outperform parametric models by a large margin on knowledge-intensive tasks. RAG also enables more factual and specific text generation.",
                "limitations": "The quality of retrieved documents heavily influences generation accuracy. RAG relies on a static document corpus and does not support real-time knowledge updates without re-indexing.",
                "keywords": ["retrieval-augmented generation", "RAG", "open-domain QA", "dense passage retrieval", "knowledge-grounded generation"],
                "content": (
                    "# Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks\n\n"
                    "## Abstract\n"
                    "Large pre-trained language models have been shown to store factual knowledge in their parameters, but their ability to access and "
                    "precisely manipulate this knowledge is still limited. We explore a general-purpose fine-tuning approach for RAG—models that combine "
                    "parametric and non-parametric memory for language generation.\n\n"
                    "## Research Goal\n"
                    "We aim to create a unified model that can (1) retrieve relevant evidence from a large knowledge corpus on-the-fly, and (2) condition "
                    "language generation on that evidence, effectively grounding responses in external knowledge rather than solely relying on trained parameters.\n\n"
                    "## Methodology\n"
                    "We use a Dense Passage Retriever (DPR) to index and retrieve top-k passages from a Wikipedia dump. A BART seq2seq model then "
                    "generates the final answer by attending over both the input query and the k retrieved passages. Two variants are explored: "
                    "RAG-Sequence (same document used for all tokens) and RAG-Token (different documents can influence each output token).\n\n"
                    "## Main Findings\n"
                    "RAG models outperform prior state-of-the-art across open-domain QA tasks and produce more factual, specific, and diverse answers. "
                    "RAG-Token achieves the best performance on most benchmarks. Generated text is more grounded and exhibits fewer hallucinations compared to purely parametric baselines.\n\n"
                    "## Limitations\n"
                    "RAG's performance depends critically on the quality and coverage of the retrieval corpus. Knowledge is frozen at indexing time; "
                    "incorporating new information requires re-building the document index, which is computationally expensive."
                )
            }
        ]

    def create_backup(self) -> bytes:
        """將 data/session_data.json 及 data/papers/ 打包為 ZIP bytes 供下載"""
        import io
        import zipfile
        from pathlib import Path

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 1. 備份 session_data.json
            session_path = Path("./data/session_data.json")
            if session_path.exists():
                zip_file.write(session_path, arcname="session_data.json")

            # 2. 備份 papers 目錄下的檔案 (含 pdf, md, json)
            papers_dir = Path("./data/papers")
            if papers_dir.exists():
                for f in papers_dir.rglob("*"):
                    if f.is_file():
                        # 計算相對路徑存入 zip，例如 papers/xxx.pdf
                        arcname = f.relative_to(Path("./data"))
                        zip_file.write(f, arcname=arcname)

        return zip_buffer.getvalue()

    def restore_backup(self, zip_bytes: bytes):
        """上傳 ZIP bytes 並還原 session_data.json 和 papers/ 目錄"""
        import io
        import zipfile
        from pathlib import Path

        zip_buffer = io.BytesIO(zip_bytes)
        
        # 先確認 papers 資料夾存在
        papers_dir = Path("./data/papers")
        papers_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            for name in zip_file.namelist():
                # 預防路徑走訪安全漏洞 (Path Traversal Protection)
                # 確保解壓目標都在 ./data 下
                target_path = (Path("./data") / name).resolve()
                if not str(target_path).startswith(str(Path("./data").resolve())):
                    continue # 略過不安全的路徑

                if name.endswith("/"):
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(zip_file.read(name))

    def get_env_variables(self) -> dict:
        """讀取 backend/.env 中的設定變數並傳回 (部分屏蔽金鑰)"""
        from pathlib import Path
        env_path = Path(".env") # 因工作目錄在 backend
        if not env_path.exists():
            env_path = Path("backend/.env")

        config = {
            "GEMINI_API_KEY": "",
            "SEMANTIC_SCHOLAR_API_KEY": "",
            "PAPERS_DB_PATH": "./data/papers",
            "GEMINI_MODEL": "gemini-3.5-flash"
        }

        if env_path.exists():
            try:
                lines = env_path.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k in config:
                            config[k] = v
            except Exception as e:
                logger.warning(f"Failed to read .env file: {e}")

        # 對金鑰進行部分屏蔽
        def mask_key(val: str) -> str:
            if not val:
                return ""
            if len(val) <= 10:
                return "******"
            return f"{val[:6]}******{val[-4:]}"

        masked_config = dict(config)
        masked_config["GEMINI_API_KEY"] = mask_key(config["GEMINI_API_KEY"])
        masked_config["SEMANTIC_SCHOLAR_API_KEY"] = mask_key(config["SEMANTIC_SCHOLAR_API_KEY"])

        return {
            "raw": config,
            "masked": masked_config
        }

    def save_env_variables(self, new_config: dict):
        """將新的設定寫入 backend/.env 檔案中，並更新 os.environ"""
        from pathlib import Path
        import os
        env_path = Path(".env")
        if not env_path.exists():
            env_path = Path("backend/.env")

        # 1. 取得舊的設定
        old_data = self.get_env_variables()
        old_raw = old_data["raw"]

        # 2. 比較並更新
        for k in ["GEMINI_API_KEY", "SEMANTIC_SCHOLAR_API_KEY", "PAPERS_DB_PATH", "GEMINI_MODEL"]:
            if k in new_config:
                val = new_config[k].strip()
                # 如果是屏蔽的表示使用者沒修改，保留原值
                if k in ["GEMINI_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"] and "******" in val:
                    continue
                old_raw[k] = val

        # 3. 寫入檔案
        try:
            lines = []
            for k, v in old_raw.items():
                lines.append(f"{k}={v}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            
            # 4. 同步更新至當前 runtime 環境變數
            for k, v in old_raw.items():
                os.environ[k] = v
        except Exception as e:
            logger.error(f"Failed to write .env file: {e}")
            raise e

    async def rebuild_rag_index(self, rag_store, agent) -> dict:
        """重新解析 data/papers/ 中的所有 PDF 並重組 RAG 索引"""
        from pathlib import Path
        from tools.rag import parse_pdf_to_markdown
        import logging

        logger = logging.getLogger("system_skill")
        db_path = Path(rag_store.db_path)
        
        # 1. 蒐集當前所有的 PDF 檔案
        pdf_files = list(db_path.glob("*.pdf"))
        
        # 2. 刪除所有現存的 md 與 json
        for f in db_path.glob("*"):
            if f.is_file() and f.suffix in [".md", ".json"]:
                f.unlink()

        # 3. 重新建立 Demo 論文（因為 Demo 論文沒有 PDF 實體檔案）
        demos = self.get_demo_papers()
        for p in demos:
            paper_id = p["paper_id"]
            title = p["title"]
            year = p["year"]
            content = p["content"]
            rag_store.add_document(paper_id, content, {"title": title, "year": year})

        # 4. 重新解析 PDF 並寫入 RAG
        reindexed_count = 0
        for pdf_path in pdf_files:
            paper_id = pdf_path.stem
            # 從 agent._summaries 找回 metadata
            meta = {"title": "未命名文獻", "year": None}
            
            found_summary = None
            for sums in agent._summaries.values():
                for s in sums:
                    if s.paper_id == paper_id:
                        found_summary = s
                        break
                if found_summary:
                    break

            if found_summary:
                meta["title"] = found_summary.title
                meta["year"] = found_summary.year

            try:
                content = parse_pdf_to_markdown(str(pdf_path))
                rag_store.add_document(paper_id, content, meta)
                reindexed_count += 1
            except Exception as e:
                logger.error(f"Failed to re-index PDF {pdf_path.name}: {e}")

        # 清除快取以促使重新計算
        agent._matrix_cache.clear()
        agent._direction_cache.clear()
        agent._save_session_data()

        return {"status": "ok", "reindexed": reindexed_count}

