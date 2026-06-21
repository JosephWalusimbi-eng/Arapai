# Arapai: Technical Report

**Project:** Arapai (Offline AI Education Tutor)  
**Problem domain:** Math & Scientific Reasoning (education tutoring)  
**Repository:** Open-source

### Key repository files

| File | Purpose |
|------|---------|
| `metadata.json` | Project metadata and reference test prompts |
| `download_model.sh` | Downloads `model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` |
| `REPORT.md` | This file |
| `model/*.gguf` | Downloaded by script; excluded from Git |

The application (`app.py`, `backend/`, etc.) provides the Streamlit tutor, CBC mode, RAG, and benchmarks.

---

## 1. Executive Summary

**Arapai** is an offline-first educational assistant named after **Arapai, Soroti District, Uganda** — where the first demo took place. In that community, poor mobile signal makes even paid data bundles slow or unusable for cloud AI. The project targets schools that need tutoring **without relying on the internet**: it runs on a standard 8 GB laptop using **GGUF models via llama.cpp**, optional **RAG over local curriculum PDFs**, **deterministic safe math**, and a **Competency-Based Curriculum (CBC) scenario quiz** with a closed learning loop: **practice → feedback → Explain my mistake**.

The system is engineered around three priorities:

- **Efficiency:** Peak RSS **703.0 MB** on the Light tier (well under a 7 GB school-laptop budget)
- **Performance:** Tier-tuned batch size, lazy model load, streaming benchmark CLI, reproducible `benchmark.py`
- **Accuracy:** Truthfulness rules, RAG grounding, hybrid CBC scoring, level-aware prompts, and structured mistake explanations

This release includes a **working prototype**: offline chat tutor, CBC-Learn, RAG over ingested PDFs, and tutor-powered mistake explanations after incorrect quiz answers.

**Cross-disciplinary integration (load-bearing):**

| Discipline | Role in Arapai |
|------------|----------------|
| On-device LLM inference | Core tutor: leveled explanations, stable offline generation |
| Information retrieval (RAG) | FAISS + sentence embeddings over ingested PDF notes |
| Structured assessment | CBC scenario questions with hybrid rubric scoring |
| Symbolic/numeric reasoning | Safe math engine for arithmetic without `eval()` |

**Deployment context:** First demo in **Arapai, Soroti District, Uganda** (severe connectivity constraints); offline school-lab design; CBC-style scenario pedagogy; target hardware ($150–$500 laptops). English UI today; local-language support planned for a future release.

---

## 2. Problem Definition

### 2.1 The problem

The project is rooted in **Arapai, Soroti District, Uganda**, where the first demo was held. There, internet access is unreliable in practice: even with data bundles purchased, poor signal often makes connectivity slow or unusable outside a few locations. That reality generalises across many school settings where cloud LLMs are impractical.

Students and teachers still face a recurring gap:

1. **Access economics** — Cloud LLMs require API fees, reliable internet, and continuous power. Many schools have none of these during normal teaching hours.
2. **Generic AI is not curriculum-aligned** — Chatbots answer broadly but do not practice CBC-style *scenario reasoning* (e.g. “A pupil connects a bulb but it does not light — explain why”) or tie answers to local course materials.
3. **One-size-fits-all explanations** — Learners at Primary, Lower Secondary, Upper Secondary, and Technical levels need different depth; a single answer frustrates both beginners and advanced students.
4. **Assessment without teaching** — Quizzes that only mark right/wrong do not close the learning loop when a student misunderstands a concept.

### 2.2 Target users

| User | Need |
|------|------|
| **Student** | Practice scenarios, ask questions offline, get explanations at their level |
| **Teacher** | Supplement lessons with an offline tutor grounded in uploaded PDFs |
| **School IT / lab admin** | Deploy once on many identical laptops without cloud dependency |

### 2.3 Success criteria

- Runs **100% offline** for inference (no network calls required during normal tutoring)
- Stays **within a 7 GB RAM budget** on typical school laptops
- Delivers **structured explanations** at selectable depth levels
- Connects **practice → feedback → explanation** in one session
- Grounds answers in **local documents** when RAG is enabled

---

## 3. Constraints

### 3.1 Hardware and runtime constraints

| Constraint | Target | Arapai response |
|------------|--------|-----------------|
| **RAM budget** | Peak RSS ≤ 7 GB on 8 GB machines | Default config uses **Light tier** (~637 MB GGUF file) |
| **Hardware profile** | 8 GB DDR4, integrated GPU, Linux or Windows | CPU inference via llama.cpp |
| **Runtime** | 100% offline during normal use | **Offline** mode is the primary path |
| **Model format** | GGUF via llama.cpp | All tiers use `models/*/model.gguf` |

### 3.2 Operational constraints (school deployment)

- **Intermittent power and no fibre** — Full offline operation after one-time setup
- **Identical lab machines** — Pinned `requirements.txt` for reproducible deployment
- **Non-technical operators** — Single-command install; Streamlit UI; default model tier is Light
- **Large model files not in Git** — GGUF weights downloaded via `download_model.sh`, `scripts/download_models.py`, or URLs in `models/MODEL_MANIFEST.json`

### 3.3 Technical constraints

- **Python 3.10 / 3.11** — Pinned stack compatible with llama-cpp-python 0.2.20
- **Context window 2048 tokens** — Bounds memory use; limits very long RAG injection
- **No arbitrary code execution** — Math limited to whitelisted numeric grammar
- **Single LLM loaded at a time** — Tier switch reloads model to bound memory
- **Windows stability** — Inference threads capped at 4; RAG unloads before LLM to reduce peak RAM

---

## 4. Design Decisions

### 4.1 Offline-first

**Decision:** Primary path is local GGUF inference via llama-cpp-python. An optional Online (Gemma 1.1) mode exists for comparison only and is **not used in normal offline deployment**.

**Rationale:** Matches school deployment reality where connectivity cannot be assumed.

### 4.2 Three model tiers (manual selection)

| Tier | Typical model | Quant | Approx. file size | Intended RAM |
|------|---------------|-------|-------------------|--------------|
| **Light** | TinyLlama 1.1B Chat | Q4_K_M | ~637 MB | Default for low-RAM labs |
| **Standard** | Llama-2 7B Chat | Q4_K_M | ~3.8 GB | 4+ GB free |
| **Advanced** | Mistral 7B Instruct v0.2 | Q4_K_M | ~4.1 GB | 8 GB (may exceed budget with RAG stack) |

**Decision:** User selects tier manually; default is Light.

**Rationale:** Predictable behaviour for IT staff; Light tier stays safely under the 7 GB RSS ceiling.

**Recommended default:** `models/lite/model.gguf` (TinyLlama Q4_K_M).

### 4.3 Four explanation levels with compliance checking

Levels: `basic`, `lower_secondary`, `upper_secondary`, `technical`.

**Decision:** Prompt rules enforce length, jargon, and structure per level. `tutor_engine.is_level_compliant()` validates output; non-compliant replies trigger a regeneration pass.

**Rationale:** Pedagogical control without larger models; validation is inexpensive on CPU.

### 4.4 RAG over local PDFs (cross-disciplinary core)

**Pipeline:**

1. PDFs placed in `data/raw_pdfs/`
2. `python -m ingestion.ingest_pdf` → chunk (500 chars, 50 overlap) → embed (`all-MiniLM-L6-v2`) → FAISS index (`ingestion/` package)
3. At query time, top-4 chunks (distance-filtered) injected as reference material in the prompt

**Decision:** RAG is optional (sidebar checkbox). Embedding model and index load only when RAG is enabled; resources are released when RAG is turned off.

**Rationale:** Teachers supply their own notes; the LLM becomes curriculum-aware without fine-tuning.

### 4.5 CBC Learning Mode + “Explain my mistake”

**Decision:** Scenario questions are stored in `data/cbc_content.json`. After each submission:

- **Correct** → feedback and “Next question”
- **Wrong / partial** → **“Explain my mistake”** returns curated offline feedback (or LLM in Online mode)

**Scoring:** Hybrid rubric — fast keyword overlap first; borderline answers (keyword score 0.25–0.55) may invoke a short LLM verdict (`cbc_engine.py`).

**Rationale:** Closes the learning loop in one offline session without requiring cloud services.

### 4.6 Safe math engine (no `eval()`)

**Decision:** Numeric expressions matching `[\d\s+\-*/().]+` are parsed and evaluated with a recursive-descent evaluator. `solve_in_text()` extracts safe sub-expressions from natural-language questions. Mixed math + explanation prompts use deterministic `build_mixed_math_reply()`.

**Rationale:** Deterministic arithmetic with no code injection risk; reliable demo and classroom behaviour on small models.

### 4.7 Modular backend

**Decision:** Core logic lives in `backend/` modules; `app.py` is the Streamlit UI entry point.

| Module | Responsibility |
|--------|----------------|
| `llm_engine.py` | Singleton model load, generate, stream, benchmark |
| `tutor_engine.py` | Level compliance and reply validation |
| `cbc_engine.py` | Hybrid answer scoring and mistake explanations |
| `rag_engine.py` | Lazy FAISS retrieval |
| `prompt_builder.py` | Level-aware and mistake-specific prompts |
| `math_engine.py` | Safe arithmetic; `solve_in_text()` for embedded expressions |
| `demo_replies.py` | Vetted sample-prompt responses |
| `memory_utils.py` | Peak RSS tracking via psutil |

---

## 5. Tools & Technology Stack

### 5.1 Core stack

| Component | Tool / version | Purpose |
|-----------|----------------|---------|
| UI | Streamlit 1.31.1 | Chat + CBC modes; stable offline chat generation |
| LLM runtime | llama-cpp-python 0.2.20 | GGUF inference (llama.cpp) |
| Model weights | GGUF (Q4_K_M / Q5_K_M) | Quantized on-device models |
| RAG embeddings | sentence-transformers 2.6.1 | `all-MiniLM-L6-v2` |
| Vector index | faiss-cpu | Top-k chunk retrieval |
| PDF parsing | pypdf | Curriculum ingestion |
| Monitoring | psutil | Peak RSS measurement |

### 5.2 Repository layout

```
app.py                  # Streamlit entry (chat + CBC-Learn)
benchmark.py            # Inference telemetry CLI
backend/
  llm_engine.py         # Model load, generate, stream, benchmark
  tutor_engine.py       # Level compliance and reply validation
  cbc_engine.py         # Hybrid CBC scoring, mistake explanations
  demo_replies.py       # Vetted sample-prompt responses
  prompt_builder.py     # Level-aware prompts
  rag_engine.py         # FAISS retrieval (lazy load)
  math_engine.py        # Safe arithmetic
  memory_utils.py       # RSS / peak memory tracking
ingestion/
  ingest_pdf.py         # Build RAG index from PDFs
  chunker.py            # Text chunking
data/
  cbc_content.json      # CBC scenario question bank
  raw_pdfs/             # Teacher-uploaded PDFs
  embeddings/           # FAISS index + chunk pickle
models/
  lite/standard/advanced/model.gguf   # Not committed; download separately
```

### 5.3 Reproduction

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux:   source venv/bin/activate
pip install -r requirements.txt

# Download default model (required; not in Git):
bash download_model.sh
# Windows alternative:
# python scripts/download_models.py

# Optional RAG:
#   Place PDFs in data/raw_pdfs/
#   python -m ingestion.ingest_pdf

streamlit run app.py
python benchmark.py --tier light
```

**Recommended configuration:** Mode = **Offline**, Model = **Light**, RAG = optional (build index before enabling).

### 5.4 Model access

Model weights are **not in Git**. Download with:

```bash
bash download_model.sh
```

This fetches **`model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`** (must match `metadata.json` → `_runtime.model_path`) and copies it to `models/lite/model.gguf` for the Streamlit app.

| Method | Purpose |
|--------|---------|
| **`bash download_model.sh`** | Primary download script (Linux/macOS) |
| `download_model.ps1` | Windows PowerShell equivalent |
| `python scripts/download_models.py` | Cross-platform alternative; syncs `model/` path |
| `models/MODEL_MANIFEST.json` | URLs for optional Standard/Advanced tiers |

**Direct URL (public, no account):**

`https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

---

## 6. Benchmarks & Evaluation

### 6.1 Evaluation priorities

| Priority | What we measure | Arapai approach |
|----------|-----------------|-----------------|
| **Accuracy** | Correct, level-appropriate tutoring | Domain prompts; RAG grounding; level compliance; hybrid CBC scoring; curated demo replies |
| **Performance** | Responsiveness on CPU | Light model; streaming in `benchmark.py`; tier-tuned `n_batch` (128 on Light); threads capped on Windows |
| **Efficiency** | Peak RAM on 8 GB laptops | TinyLlama tier; lazy RAG load; RAG unloads before LLM; measured peak RSS 703.0 MB |

### 6.2 Recommended test configuration

| Setting | Value |
|---------|-------|
| OS | Ubuntu 22.04 LTS or Windows 10/11 |
| Model file | `models/lite/model.gguf` (TinyLlama 1.1B Chat Q4_K_M) |
| Mode | Offline |
| `n_ctx` | 2048 |
| `max_tokens` | 256 (default generation cap) |
| RAG | Off for inference telemetry; On for curriculum-grounded demos |

Standard and Advanced tiers are available for quality demos but may approach the 7 GB RSS limit when combined with the RAG embedding stack.

### 6.3 Reference test prompts

Two reference prompts used to validate math and scientific reasoning:

#### Prompt A — Scientific reasoning (Ohm’s Law scenario)

**User prompt:**

> A student connects a thin, long wire in a circuit and notices the bulb is dimmer than when using a short, thick wire. Explain why this happens.

**Expected qualities:**

- Resistance increases with wire length and decreases with cross-sectional area
- Lower current produces a dimmer bulb
- At `basic` level: 1–2 simple sentences, no jargon
- At `technical` level: numbered steps with correct terminology

**Curated demo output (Light tier, `lower_secondary`, offline):**

> A longer, thinner wire has higher resistance than a short, thick one. Higher resistance reduces the current in the circuit, so the bulb receives less power and glows dimmer.

#### Prompt B — Quantitative reasoning (safe math + concept)

**User prompt:**

> What is (48 / 6) + 7 * 2? Then explain in one sentence what order of operations means.

**Expected qualities:**

- Math engine returns **22** for `(48÷6)+7×2 = 8+14` via `solve_in_text()`
- Explanation of order of operations at the selected level
- No meta-commentary or self-description

**Sample results (Light tier, `lower_secondary`, offline):**

| Component | Result |
|-----------|--------|
| Math engine | `solve("(48/6)+7*2")` → **22**; `solve_in_text(...)` → **22** |
| Combined reply | `(48 / 6) + 7 * 2 = 22. Order of operations means brackets first, then multiplication and division, then addition and subtraction.` |

### 6.4 Functional validation

| Test | Method | Result |
|------|--------|--------|
| Offline inference | Network disabled; chat and CBC explain | Pass |
| Level compliance | `tutor_engine.is_level_compliant()` | Pass |
| Math safety | `solve("import os")` → `None` | Pass |
| Math correctness | `solve("(48/6)+7*2")` → `22` | Pass |
| Mixed math in text | `solve_in_text("What is (48 / 6) + 7 * 2? Then explain…")` → `22` | Pass |
| RAG retrieval | Ingest PDF; query related term | Pass when index built |
| CBC loop | Wrong answer → Explain my mistake | Pass |
| Memory (Light, RAG off) | `python benchmark.py --tier light` | Peak RSS **703.0 MB** |

### 6.5 Measured benchmark results (Light tier)

Command: `python benchmark.py --tier light`

Output is written to `benchmark_results.json`. Example from the latest reproducible run:

**Measurement environment:** Windows development machine, CPU inference, RAG disabled, TinyLlama Q4_K_M, streaming enabled in benchmark CLI. Reproduce on your target school laptop for comparable results.

| Metric | Light tier |
|--------|------------|
| Peak RSS (MB) | **703.0** |
| Tokens/sec (TPS) | **3.67** |
| Time to first token (s) | **1.59** |
| Total latency, 256-token cap (s) | **8.68** |
| Thermal throttle | Not measured in this run |

**Headroom:** `100 × (7168 − 703) / 7168 ≈ 90` — substantial margin under a 7 GB budget.

---

## 7. Current Deliverable

| Feature | Status |
|---------|--------|
| Offline GGUF chat tutor | Shipped |
| Four explanation levels + compliance retry | Shipped |
| Offline chat generation (stable non-streaming UI) | Shipped |
| Streaming telemetry in `benchmark.py` | Shipped |
| Safe numeric math | Shipped |
| RAG over local PDFs | Shipped (requires `python -m ingestion.ingest_pdf`) |
| CBC scenario quiz | Shipped |
| Explain my mistake (curated offline + LLM online) | Shipped |
| Hybrid CBC scoring | Shipped |
| Multi-tier model selector | Shipped |
| Sample demo prompts in UI | Shipped |
| Benchmark CLI (`benchmark.py`) | Shipped |

**Sample curriculum:** `data/cbc_content.json` — Primary / Lower Secondary / Upper Secondary / Technical (e.g. Basic Electricity, Ohm’s Law, Electrical Installation).

**Sample reference PDF:** `data/raw_pdfs/Computer Networks and Data Communication_Lecture 1.pdf`

---

## 8. Future Work

- Scenario generation from ingested PDFs with teacher review
- Persistent progress tracking and teacher reporting
- Swahili and additional local-language UI
- One-click lab installer and pre-built RAG index for school deployment
- Broader hardware validation on Ubuntu and low-cost school laptops
- Stronger models on Standard/Advanced tiers where RAM allows

---

## 9. Deployment Context

| Aspect | Notes |
|--------|-------|
| **Origin** | Named for Arapai, Soroti District, Uganda — first demo site with severe connectivity limits |
| **Target hardware** | 8 GB laptops (~$150–$500); Light tier peak RSS ~703 MB |
| **Pedagogy** | CBC-style scenario questions; four explanation levels |
| **Language** | English UI today; local-language support planned |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OOM on 8 GB with 7B + RAG | Default to Light tier; lazy RAG load; RAG optional |
| Small-model answer quality | RAG grounding; curated demo replies; deterministic math; Standard tier where RAM allows |
| Borderline CBC grading | Hybrid keyword + LLM rubric; Explain my mistake loop |
| Missing RAG index | Clear UI warning; `python -m ingestion.ingest_pdf` |
| Native inference crash (Windows) | Thread cap, lower `n_batch`, RAG unload before LLM, safe-mode retry |
| Thermal throttling | Light model default; CPU-first inference |

---

## 11. Reproduction Checklist

| Step | Action |
|------|--------|
| 1 | Clone the repository |
| 2 | `pip install -r requirements.txt` |
| 3 | **`bash download_model.sh`** — fetches `model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` |
| 4 | `streamlit run app.py` — Mode: **Offline**, Model: **Light** |
| 5 | Try sample prompts; open **CBC-Learn**; test **Explain my mistake** |
| 6 | Optional RAG: add PDFs → `python -m ingestion.ingest_pdf` → enable RAG checkbox |
| 7 | `python benchmark.py --tier light` for telemetry output |

**Model manifest:** `models/MODEL_MANIFEST.json` · **Full instructions:** `models/README.md`

---

*Arapai - Offline AI that schools can own, run, and trust.*
