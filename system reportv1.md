# Arapai – System Report v1

**Document:** Full system analysis  
**Product:** Arapai – Offline AI Education ChatBot  
**Scope:** Features, functionalities, architecture, deployment

---

## 1. Executive Summary

Arapai is an **offline-first educational chatbot** that runs a local GGUF language model (via llama.cpp), with optional RAG over user-provided PDFs and safe numeric expression evaluation. It is designed for deployment on school or lab machines without internet dependency after setup. The UI is a single-page Streamlit chat app with explanation-level control, model-tier selection, and streaming responses.

---

## 2. High-Level Features

| Feature | Description |
|--------|-------------|
| **Offline LLM chat** | Local inference using GGUF models (llama-cpp-python); no cloud API. |
| **Multi-tier models** | Manual selection of Light / Standard / Advanced model tiers. |
| **Streaming responses** | Token-by-token output for faster perceived response time (Ollama-style). |
| **Explanation levels** | Six levels: basic, basic_detailed, standard, standard_detailed, advanced, advanced_detailed. |
| **Optional RAG** | “Use reference documents (PDFs)” retrieves relevant chunks from indexed PDFs and injects them into the prompt. |
| **Safe math** | Pure numeric expressions (+, -, *, /, parentheses) are evaluated safely without `eval()` of arbitrary code. |
| **Edit & regenerate** | User can edit the last question and regenerate the assistant reply. |
| **New chat** | Clears conversation and resets chat state. |

---

## 3. Functional Overview

### 3.1 User flow

1. **Start** – User opens the app; session state is initialized (messages, level, model tier, etc.); LLM is warmed up on first load.
2. **Configure** – User selects explanation level and model (Light / Standard / Advanced), and optionally enables “Use reference documents (PDFs)”.
3. **Ask** – User types a question in the chat input.
4. **Process** – For each turn:
   - **Math:** If the input is a numeric-only expression, `math_engine.solve()` returns the result and the assistant replies with that result only (no LLM).
   - **RAG (if enabled):** Query is sent to `rag_engine.retrieve()`; top-k text chunks are fetched from the FAISS index and passed into the prompt.
   - **Prompt:** `prompt_builder.build_prompt(level, history, retrieved_text)` builds the full prompt with system instruction, reference material (if any), and conversation history (last 6 messages).
   - **LLM:** Either `generate_stream()` (main chat; streaming) or `generate()` (e.g. regenerate; non-streaming) is called with the chosen model tier.
5. **Display** – Assistant message is shown (streamed with a cursor in main chat, or at once when regenerating).
6. **Edit (optional)** – User can click “Edit last question”, change the text, then “Save & Regenerate” or “Cancel”.
7. **New chat** – “New Chat” clears messages and resets edit state.

### 3.2 Model selection

- **Manual only:** User selects Light, Standard, or Advanced; backend requires the selected GGUF file.
- **Default:** The model selector defaults to Light for stable startup.
- **Lazy load:** The LLM is loaded on first use (or when tier changes). Switching tier in the UI causes the next request to load the new model.

### 3.3 RAG (reference documents)

- **Data:** PDFs in `data/raw_pdfs` or `data/rawpdfs` are ingested by `python -m ingestion.ingest_pdf`.
- **Ingestion:** PDFs are read (pypdf), text is chunked (500 chars, 50 overlap), embedded with SentenceTransformer `all-MiniLM-L6-v2`, and stored in FAISS (`data/embeddings/index.faiss`) plus a pickle of texts (`data/embeddings/texts.pkl`).
- **Retrieval:** At query time, the same embedding model encodes the query; FAISS returns top-k (default 3) nearest chunks; concatenated text is added to the prompt as “Reference Material”.

### 3.4 Safe math

- **Scope:** Only digits, spaces, and `+ - * / ( )` are allowed. No letters or other symbols.
- **Behavior:** Parsed and evaluated with a small recursive-descent style evaluator; no `eval()` or execution of arbitrary code. Returns `None` on invalid input or division by zero; otherwise the numeric result is shown as the assistant reply.

---

## 4. Architecture

### 4.1 Component diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  app.py (Streamlit UI)                                           │
│  - Session state, level/model_tier, use_rag                      │
│  - Chat display, edit mode, regenerate, new chat                 │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ├── backend/llm_engine   (warm_up, generate, generate_stream)
                ├── backend/prompt_builder (build_prompt, LEVELS)
                ├── backend/rag_engine (retrieve)
                └── backend/math_engine (solve)
                │
                │  ingestion/ (offline)
                │  - ingest_pdf.py (builds index from PDFs)
                │  - chunker.py (chunk_text)
                │
                │  data/
                │  - raw_pdfs/ or rawpdfs/  (input PDFs)
                │  - embeddings/index.faiss, texts.pkl
                │
                │  models/
                │  - lite/model.gguf, standard/model.gguf, advanced/model.gguf
```

### 4.2 Backend modules

| Module | Role |
|--------|------|
| **llm_engine** | Manual model path resolution, lazy Llama load with optional GPU (`n_gpu_layers=-1`), batch threading, `warm_up()`, `generate()`, `generate_stream()`. |
| **prompt_builder** | `LEVELS` (six explanation levels in strict progression), labels/order constants, and `build_prompt(level, history, retrieved_text)`. |
| **rag_engine** | Loads SentenceTransformer and FAISS index on first use; `retrieve(query, top_k=3)` returns concatenated top-k chunks. |
| **math_engine** | Whitelist regex + tokenizer + recursive expression evaluator; `solve(expression)` returns float or None. |

### 4.3 Data and file layout

| Path | Purpose |
|------|--------|
| `app.py` | Streamlit entry point. |
| `backend/*.py` | LLM, prompts, RAG, math. |
| `ingestion/ingest_pdf.py` | Build RAG index from PDFs. |
| `ingestion/chunker.py` | Text chunking (500 chars, 50 overlap). |
| `data/raw_pdfs` or `data/rawpdfs` | Input PDFs for RAG. |
| `data/embeddings/index.faiss` | FAISS vector index. |
| `data/embeddings/texts.pkl` | Chunk texts corresponding to index. |
| `models/lite/model.gguf` | Lite tier model (any RAM). |
| `models/standard/model.gguf` | Standard tier (4+ GB RAM). |
| `models/advanced/model.gguf` | Advanced tier (8+ GB RAM). |

---

## 5. Dependencies and Deployment

### 5.1 Core stack

- **streamlit** 1.31.1 – UI.
- **llama-cpp-python** 0.2.20 – GGUF inference (CPU by default; optional CUDA build).
- **numpy**, **pypdf**, **faiss-cpu**, **psutil** – Utilities, PDF, vector index, RAM check.
- **huggingface-hub**, **transformers**, **sentence-transformers** (pinned) – RAG embedding model.

### 5.2 Install

- **Default (any device):** `pip install -r requirements.txt` (with venv activated). Single command for full CPU setup.
- **Optional GPU:** Set `CMAKE_ARGS=-DGGML_CUDA=on`, then `pip install -r requirements-gpu.txt --no-cache-dir --force-reinstall`. Requires NVIDIA GPU + CUDA Toolkit. See `howtorun.txt`.

### 5.3 Run

- From project root: `streamlit run app.py`.
- Python 3.10 or 3.11 recommended; 3.12 can cause issues with llama-cpp.

### 5.4 Model files

- User must place at least one GGUF file as `model.gguf` in one of `models/lite/`, `models/standard/`, or `models/advanced/`.
- Recommended: Q4_K_M or Q5_K_M quantized models. Exact download links and steps are in `models/README.md` and `howtorun.txt`.

---

## 6. Security and Safety

- **No arbitrary code execution:** Math is restricted to a small expression grammar and evaluated without `eval()` of user-supplied code.
- **Offline:** No telemetry or external API calls for inference; RAG and LLM run locally.
- **Pinned dependencies:** Requirements are pinned for reproducible deployment across many machines.

---

## 7. Limitations and Notes

- **Single process:** One Streamlit process; one LLM loaded at a time (per tier). Switching tier reloads the model.
- **RAG is optional:** If “Use reference documents” is off or index is missing, no reference material is added.
- **No authentication:** The app does not implement login or access control.
- **Windows-focused docs:** `howtorun.txt` emphasizes Windows (venv path, Visual C++ Build Tools, CUDA instructions). Same Python flow applies on other OS with appropriate paths and build tools.

### 7.1 Known console messages and errors

- **`torch.classes` / `Tried to instantiate class '__path__._path', but it does not exist!`**  
  This message comes from the PyTorch / Hugging Face stack (e.g. sentence-transformers or transformers), not from Arapai or llama-cpp. It is a benign warning and can be ignored; it does not affect chatbot or RAG behaviour. Optionally set `TORCH_SHOW_CPP_STACKTRACES=0` to reduce PyTorch verbosity.

- **`AssertionError()` when using the Advanced model**  
  On some systems the Advanced (e.g. 7B) model can trigger an assertion inside the inference stack. The UI will suggest trying **Standard** or **Light** in the Model menu. Use the Model dropdown to select a smaller tier if this occurs.

---

## 8. Summary Table

| Aspect | Detail |
|--------|--------|
| **Purpose** | Offline educational chatbot with local LLM, optional PDF RAG, safe math. |
| **UI** | Streamlit; one page; chat + level + model + RAG checkbox + edit/regenerate/new chat. |
| **LLM** | GGUF via llama-cpp-python; manual tier selection; streaming in main chat. |
| **RAG** | PDFs → chunk → embed (MiniLM) → FAISS; retrieve top-k into prompt. |
| **Math** | Safe numeric expressions only; no eval of code. |
| **Install** | `pip install -r requirements.txt`; optional GPU via `requirements-gpu.txt`. |
| **Run** | `streamlit run app.py` from project root. |

---

*End of System Report v1*
