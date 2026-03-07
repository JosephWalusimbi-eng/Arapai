# Arapai – Offline AI Education ChatBot

Offline chatbot for education: local GGUF LLM, optional RAG over your PDFs, and safe math evaluation.

## Quick start

1. **Install** (from project root):
   ```bash
   pip install -r requirements.txt
   ```
2. **Add a GGUF model**: put `model.gguf` in one of:
   - `models/lite/` (any RAM)
   - `models/standard/` (4+ GB free RAM)
   - `models/advanced/` (8+ GB free RAM)
   See `models/README.md` for examples.
3. **Run**:
   ```bash
   streamlit run app.py
   ```

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
