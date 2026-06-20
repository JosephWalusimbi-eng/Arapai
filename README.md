# Arapai — Offline AI Education Tutor

**On-device AI tutoring for schools — no cloud required.**

Arapai is named after **Arapai, a community in Soroti District, Uganda**, where the project was first demoed. Even with data bundles loaded, internet access is often slow or unusable except in a few spots with decent signal. The goal is simple: **AI that schools can own, run, and trust offline** — without the internet as a constraint.

Built for the [Africa Deep Tech Challenge 2026 — Laptop LLM Challenge](https://africadeeptech.org/challenge-2026). Full technical report: [`REPORT.md`](REPORT.md) · DevPost story: [`ABOUT.md`](ABOUT.md)

---

## What it does

| Feature | Description |
|---------|-------------|
| **Offline chat tutor** | Local GGUF model (TinyLlama Light tier) via llama.cpp |
| **Explanation levels** | Basic → Lower Secondary → Upper Secondary → Technical |
| **Safe math** | Deterministic arithmetic (no `eval()`); mixed calculate-then-explain prompts |
| **CBC-Learn** | Scenario quiz with feedback and **Explain my mistake** |
| **Optional RAG** | FAISS + sentence embeddings over teacher PDFs |
| **Sample prompts** | Three demo-ready prompts for quick testing |

Peak memory on the Light tier: **~703 MB** (under the ADTC 7 GB ceiling).

---

## Quick start

### 1. Install (venv recommended)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Download the audit model (not in Git)

```bash
bash download_model.sh
```

**Windows:** `.\download_model.ps1` or `python scripts/download_models.py`

### 3. Run

```bash
streamlit run app.py
```

**Recommended demo settings:** Mode = **Offline**, Model = **Light**, RAG = off (unless index is built).

### 4. Benchmark (optional)

```bash
python benchmark.py --tier light
```

---

## Optional: RAG (reference documents)

1. Put PDFs in `data/raw_pdfs/`
2. Build the index:
   ```bash
   python -m ingestion.ingest_pdf
   ```
3. Enable **Use reference documents (RAG)** in the sidebar

---

## Optional: GPU acceleration

On NVIDIA + CUDA, see `howtorun.txt` and `requirements-gpu.txt`. CPU-only is the default and ADTC audit path.

---

## Online mode (dev / comparison only)

**Online (Gemma 1.1)** uses Hugging Face Inference API — requires `HF_TOKEN`. Not used for ADTC offline audit.

---

## Project layout

```
app.py              Streamlit UI (chat + CBC-Learn)
benchmark.py        ADTC telemetry CLI
backend/            LLM, tutor, math, RAG, CBC engines
ingestion/          PDF chunking and FAISS index build
data/               CBC questions, PDFs, embeddings
models/             GGUF tiers (download separately)
metadata.json       ADTC submission metadata
download_model.sh   ADTC-required model fetch script
```

---

## ADTC submission files

| File | Purpose |
|------|---------|
| `metadata.json` | Team metadata and test prompts |
| `REPORT.md` | Judge-ready technical report |
| `download_model.sh` | Fetches audit GGUF to `model/` |
| `ABOUT.md` | DevPost project story |

Before DevPost submit: fill `team_id` in `metadata.json`.

---

## Themes

Light and Dark themes are available in the sidebar (warm cream / cocoa palettes).

---

## License & context

Open-source submission for ADTC 2026. Competency-Based Curriculum (CBC) scenario content aligns with scenario-style school assessment. English UI today; additional local languages planned.

*Arapai — offline AI that schools can own, run, and trust.*
