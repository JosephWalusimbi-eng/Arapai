# Arapai – Offline AI Education ChatBot

Offline chatbot for education: local GGUF LLM, optional RAG over your PDFs, and safe math evaluation.

## Themes & Aesthetics

Arapai now features a **Warm Theme** designed for comfortable, long-term learning:
- **Warm Light Mode**: Soft cream backgrounds (`#fdfaf6`) and espresso text to reduce eye strain.
- **Warm Dark Mode**: Deep cocoa backgrounds (`#1a1614`) with amber accents for a focused, evening-friendly experience.
- Accessible via the "Theme" dropdown in the sidebar.

## Quick start

1. **Install** (from project root, with venv activated):
   ```bash
   pip install -r requirements.txt
   ```
   This single command installs everything needed to run on any device (CPU). No other pip steps required.
2. **Download the audit model** (not in Git):
   ```bash
   bash download_model.sh
   ```
   On Windows: `python scripts/download_models.py` (syncs the same ADTC `model/` path).
3. **Fill `metadata.json`** — replace `FILL_*` placeholders before DevPost submission.
4. **Run**:
   ```bash
   streamlit run app.py
   ```

**Optional: GPU acceleration** – On machines with an NVIDIA GPU and CUDA installed, you can install a GPU-backed `llama-cpp-python` for much faster inference. See `howtorun.txt` section “OPTIONAL: GPU ACCELERATION”.

## Online Mode

Arapai supports an **Online Mode** (Gemma 1.1) for users who want to compare local performance with cloud-based inference.
- Requires a Hugging Face token (`HF_TOKEN`) set as an environment variable.
- Uses the `google/gemma-1.1-7b-it` model via the Hugging Face Inference API.

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
