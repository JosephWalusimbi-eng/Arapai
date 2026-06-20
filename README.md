# Arapai — Offline AI Education Tutor

**On-device AI tutoring for schools — no cloud required.**

Arapai is named after **Arapai, a community in Soroti District, Uganda**, where the project was first demoed. Even with data bundles loaded, internet access is often slow or unusable except in a few spots with decent signal. The goal is simple: **AI that schools can own, run, and trust offline** — without the internet as a constraint.

Named after **Arapai, Soroti District, Uganda** — where the first demo took place. Full technical report: [`REPORT.md`](REPORT.md) · Project story: [`ABOUT.md`](ABOUT.md)

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

Peak memory on the Light tier: **~703 MB** (comfortably under a 7 GB school-laptop budget).

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

### 2. Download the default model (not in Git)

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

On NVIDIA + CUDA, see `howtorun.txt` and `requirements-gpu.txt`. CPU-only is the default offline path.

---

## Online mode (dev / comparison only)

**Online (Gemma 1.1)** uses Hugging Face Inference API — requires `HF_TOKEN`. Not used for normal offline deployment.

---

## Project layout

```
app.py              Streamlit UI (chat + CBC-Learn)
benchmark.py        Inference telemetry CLI
backend/            LLM, tutor, math, RAG, CBC engines
ingestion/          PDF chunking and FAISS index build
data/               CBC questions, PDFs, embeddings
models/             GGUF tiers (download separately)
metadata.json       Project metadata and test prompts
download_model.sh   Model download script
```

---

## Key documentation

| File | Purpose |
|------|---------|
| `metadata.json` | Project metadata and reference test prompts |
| `REPORT.md` | Technical report |
| `download_model.sh` | Fetches default GGUF to `model/` |
| `ABOUT.md` | Project story and motivation |

Fill `team_id` in `metadata.json` if required for your submission platform.

---

## Themes

Light and Dark themes are available in the sidebar (warm cream / cocoa palettes).

---

## License & context

Open-source offline education tutor. Competency-Based Curriculum (CBC) scenario content aligns with scenario-style school assessment. English UI today; additional local languages planned.

*Arapai — offline AI that schools can own, run, and trust.*
