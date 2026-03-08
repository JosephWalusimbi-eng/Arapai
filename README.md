# Arapai – Offline AI Education ChatBot

Offline chatbot for education: local GGUF LLM, optional RAG over your PDFs, and safe math evaluation.

## Quick start

1. **Install** (from project root, with venv activated):
   ```bash
   pip install -r requirements.txt
   ```
   This single command installs everything needed to run on any device (CPU). No other pip steps required.
2. **Add a GGUF model**: put `model.gguf` in one of:
   - `models/lite/` (any RAM)
   - `models/standard/` (4+ GB free RAM)
   - `models/advanced/` (8+ GB free RAM)
   Prefer **Q4_K_M** or **Q5_K_M** quantized models for speed. See `models/README.md` for exact download links.
3. **Run**:
   ```bash
   streamlit run app.py
   ```

**Optional: GPU acceleration** – On machines with an NVIDIA GPU and CUDA installed, you can install a GPU-backed `llama-cpp-python` for much faster inference. See `howtorun.txt` section “OPTIONAL: GPU ACCELERATION”.

## Optional: RAG (reference documents)

1. Put PDFs in `data/raw_pdfs` or `data/rawpdfs`.
2. Build the index:
   ```bash
   python -m ingestion.ingest_pdf
   ```
3. Enable “Use reference documents (PDFs)” in the app.

## Project layout

- `app.py` – Streamlit UI
- `backend/` – LLM, prompts, RAG, safe math
- `ingestion/` – PDF chunking and embedding index
