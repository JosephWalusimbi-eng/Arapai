# Arapai — ADTC 2026 Submission Report

**Project:** Arapai (Offline AI Education Tutor)  
**Challenge:** [Africa Deep Tech Challenge 2026 — The Laptop LLM Challenge](https://africadeeptech.org/challenge-2026)  
**Problem domain:** Math & Scientific Reasoning (education tutoring)  
**Submission gate:** Gate 1 — Submission Package (deadline: 24 July 2026)  
**Repository:** Open-source; aligned with the [ADTC 2026 submission template](https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template)

### ADTC required files (repo root)

| Template file | Status |
|---------------|--------|
| `metadata.json` | Present — **fill `team_id` before DevPost submit** (email and GitHub handle set) |
| `download_model.sh` | Present — downloads to `model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` |
| `REPORT.md` | Present (this file) |
| `model/*.gguf` | Downloaded by script; excluded from Git |

The full Arapai application (`app.py`, `backend/`, etc.) extends the template with the Streamlit tutor, CBC mode, RAG, and benchmarks.

---

## 1. Executive Summary

**Arapai** is an offline-first educational assistant for schools that cannot rely on cloud APIs, stable fibre, or sustained electricity. It runs on a standard 8 GB laptop using **GGUF models via llama.cpp**, optional **RAG over local curriculum PDFs**, **deterministic safe math**, and a **Competency-Based Curriculum (CBC) scenario quiz** with a closed learning loop: **practice → feedback → Explain my mistake**.

The system is engineered for ADTC scoring dimensions:

- **S_eff:** Peak RSS **703.0 MB** on the Light tier (well under the 7 GB disqualification ceiling)
- **S_perf:** Tier-tuned batch size, lazy model load, streaming benchmark CLI, reproducible `benchmark.py`
- **S_acc:** Truthfulness rules, RAG grounding, hybrid CBC scoring, level-aware prompts, and structured mistake explanations

This submission includes a **working prototype**: offline chat tutor, CBC-Learn, RAG over ingested PDFs, and tutor-powered mistake explanations after incorrect quiz answers.

**Cross-disciplinary integration (load-bearing):**

| Discipline | Role in Arapai |
|------------|----------------|
| On-device LLM inference | Core tutor: leveled explanations, stable offline generation |
| Information retrieval (RAG) | FAISS + sentence embeddings over ingested PDF notes |
| Structured assessment | CBC scenario questions with hybrid rubric scoring |
| Symbolic/numeric reasoning | Safe math engine for arithmetic without `eval()` |

**African context:** Offline school labs, CBC-style scenario pedagogy, and deployment on low-cost hardware ($150–$500). English UI today; local-language support planned for a future release.

---

## 2. Problem Definition

### 2.1 The problem

Across Africa, students and teachers face a recurring gap:

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

- Runs **100% offline** during ADTC audit (no network calls for inference)
- Stays **within the 7 GB RAM ceiling** on the ADTC Standard Laptop
- Delivers **structured explanations** at selectable depth levels
- Connects **practice → feedback → explanation** in one session
- Grounds answers in **local documents** when RAG is enabled

---

## 3. Constraints

### 3.1 ADTC hardware and scoring constraints

| Constraint | Requirement | Arapai response |
|------------|-------------|-----------------|
| **RAM ceiling** | Peak RSS ≤ 7 GB; OOM → disqualification | Default audit config uses **Light tier** (~637 MB GGUF file) |
| **Hardware profile** | 8 GB DDR4, integrated GPU, Ubuntu 22.04 | CPU inference via llama.cpp |
| **Runtime** | 100% offline during testing | **Offline** mode is the audit path |
| **Model format** | GGUF via llama.cpp only | All tiers use `models/*/model.gguf` |
| **Scoring** | S_total = 0.50·S_acc + 0.30·S_perf + 0.20·S_eff − P_thermal | Optimised for accuracy, tokens/sec, and low peak RAM |

### 3.2 Operational constraints (African schools)

- **Intermittent power and no fibre** — Full offline operation after one-time setup
- **Identical lab machines** — Pinned `requirements.txt` for reproducible deployment
- **Non-technical operators** — Single-command install; Streamlit UI; default model tier is Light
- **Large model files not in Git** — GGUF weights downloaded via `scripts/download_models.py` or URLs in `models/MODEL_MANIFEST.json`

### 3.3 Technical constraints

- **Python 3.10 / 3.11** — Pinned stack compatible with llama-cpp-python 0.2.20
- **Context window 2048 tokens** — Bounds memory use; limits very long RAG injection
- **No arbitrary code execution** — Math limited to whitelisted numeric grammar
- **Single LLM loaded at a time** — Tier switch reloads model to bound memory
- **Windows stability** — Inference threads capped at 4; RAG unloads before LLM to reduce peak RAM

---

## 4. Design Decisions

### 4.1 Offline-first

**Decision:** Primary path is local GGUF inference via llama-cpp-python. An optional Online (Gemma 1.1) mode exists for comparison only and is **not used for ADTC audit**.

**Rationale:** Matches ADTC mandate and school deployment reality.

### 4.2 Three model tiers (manual selection)

| Tier | Typical model | Quant | Approx. file size | Intended RAM |
|------|---------------|-------|-------------------|--------------|
| **Light** | TinyLlama 1.1B Chat | Q4_K_M | ~637 MB | Any (audit default) |
| **Standard** | Llama-2 7B Chat | Q4_K_M | ~3.8 GB | 4+ GB free |
| **Advanced** | Mistral 7B Instruct v0.2 | Q4_K_M | ~4.1 GB | 8 GB (may exceed budget with RAG stack) |

**Decision:** User selects tier manually; default is Light.

**Rationale:** Predictable behaviour for IT staff; Light tier stays safely under the 7 GB RSS ceiling.

**Audit recommendation:** `models/lite/model.gguf` (TinyLlama Q4_K_M).

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
- **Wrong / partial** → optional **“Explain my mistake”** invokes the tutor pipeline (explanation level + optional RAG + compliance retry)

**Scoring:** Hybrid rubric — fast keyword overlap first; borderline answers (keyword score 0.25–0.55) may invoke a short LLM verdict (`cbc_engine.py`).

**Rationale:** Closes the learning loop in one offline session without requiring cloud services.

### 4.6 Safe math engine (no `eval()`)

**Decision:** Numeric expressions matching `[\d\s+\-*/().]+` are parsed and evaluated with a recursive-descent evaluator. `solve_in_text()` extracts safe sub-expressions from natural-language questions (e.g. “What is (48 / 6) + 7 * 2? Then explain…”).

**Rationale:** Deterministic arithmetic with no code injection risk. Pure numeric input bypasses the LLM entirely. Mixed math + explanation prompts inject the computed result into the tutor prompt so the model explains with the correct value.

### 4.7 Modular backend

**Decision:** Core logic lives in `backend/` modules; `app.py` is the Streamlit UI entry point.

| Module | Responsibility |
|--------|----------------|
| `llm_engine.py` | Singleton model load, generate, stream, benchmark |
| `tutor_engine.py` | Level compliance and reply validation |
| `cbc_engine.py` | Hybrid answer scoring and mistake prompts |
| `rag_engine.py` | Lazy FAISS retrieval |
| `prompt_builder.py` | Level-aware and mistake-specific prompts |
| `math_engine.py` | Safe arithmetic; `solve_in_text()` for embedded expressions |
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
benchmark.py            # ADTC telemetry CLI
backend/
  llm_engine.py         # Model load, generate, stream, benchmark
  tutor_engine.py       # Level compliance and reply validation
  cbc_engine.py         # Hybrid CBC scoring, mistake prompts
  prompt_builder.py     # Level-aware prompts
  rag_engine.py         # FAISS retrieval (lazy load)
  math_engine.py        # Safe arithmetic
  memory_utils.py       # RSS / peak memory tracking
  explanation_levels.py # Explanation schema utilities
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

# Download audit model (required; not in Git):
bash download_model.sh
# Windows alternative:
# python scripts/download_models.py

# Optional RAG:
#   Place PDFs in data/raw_pdfs/
#   python -m ingestion.ingest_pdf

streamlit run app.py
python benchmark.py --tier light
```

**Audit configuration:** Mode = **Offline**, Model = **Light**, RAG = optional (build index before RAG demo).

### 5.4 Model access (for judges)

Per the [ADTC submission template](https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template), weights are **not in Git**. Judges run:

```bash
bash download_model.sh
```

This downloads the audit model to **`model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`** (must match `metadata.json` → `_runtime.model_path`) and copies it to `models/lite/model.gguf` for the Streamlit app.

| Method | Purpose |
|--------|---------|
| **`bash download_model.sh`** | **Required for ADTC profiler** (`adtc-profiler run --submission .`) |
| `metadata.json` | Team metadata and exactly **2 test prompts** |
| `python scripts/download_models.py` | Windows-friendly alternative; also syncs ADTC `model/` path |
| `models/MODEL_MANIFEST.json` | URLs for optional Standard/Advanced tiers |

**Direct URL (public, no account):**

`https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`

---

## 6. Benchmarks & Evaluation

### 6.1 ADTC scoring model

```
S_total = 0.50 × S_acc + 0.30 × S_perf + 0.20 × S_eff − P_thermal
```

| Metric | Weight | Arapai strategy |
|--------|--------|-----------------|
| **S_acc** | 50% | Domain prompts; RAG grounding; level compliance; hybrid CBC scoring |
| **S_perf** | 30% | Light model; streaming in `benchmark.py`; tier-tuned `n_batch` (128 on Light); threads capped on Windows |
| **S_eff** | 20% | TinyLlama tier; lazy RAG load; RAG unloads before LLM; measured peak RSS 703.0 MB |
| **P_thermal** | −10 | CPU-first Light tier; optional GPU via `ARAPAI_GPU=1` |

Official profiling: [ADTC profiler](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler) on Ubuntu 22.04 / 8 GB hardware.

### 6.2 Recommended audit configuration

| Setting | Value |
|---------|-------|
| OS | Ubuntu 22.04 LTS |
| Model file | `models/lite/model.gguf` (TinyLlama 1.1B Chat Q4_K_M) |
| Mode | Offline |
| `n_ctx` | 2048 |
| `max_tokens` | 256 (default generation cap) |
| RAG | Off for LLM telemetry; On for curriculum-grounded accuracy demo |

Standard and Advanced tiers are available for quality demos but may approach the 7 GB RSS limit when combined with the RAG embedding stack.

### 6.3 Submission test prompts

Per ADTC rules, two prompts are submitted here; organisers add two hidden prompts in the same domain.

#### Prompt A — Scientific reasoning (Ohm’s Law scenario)

**User prompt:**

> A student connects a thin, long wire in a circuit and notices the bulb is dimmer than when using a short, thick wire. Explain why this happens.

**Expected qualities:**

- Resistance increases with wire length and decreases with cross-sectional area
- Lower current produces a dimmer bulb
- At `basic` level: 1–2 simple sentences, no jargon
- At `technical` level: numbered steps with correct terminology

**Sample output (Light tier, `lower_secondary`, offline):**

> The bulb's warmth can cause the thin wire to heat up, making it a less effective insulator for the longer wire. This results in the bulb being dimmed due to its increased resistance to electrical current flow.

**Assessment:** The Light model partially identifies resistance but conflates heating with insulation. **Mitigations in this submission:** RAG over ingested curriculum PDFs, level-compliance retry, and Standard tier for higher-quality explanations.

#### Prompt B — Quantitative reasoning (safe math + concept)

**User prompt:**

> What is (48 / 6) + 7 * 2? Then explain in one sentence what order of operations means.

**Expected qualities:**

- Math engine returns **22** for `(48÷6)+7×2 = 8+14` (pure or embedded in text via `solve_in_text()`)
- LLM explains order of operations at the selected level using the injected numeric result
- No meta-commentary or self-description

**Sample results (Light tier, `lower_secondary`, offline):**

| Component | Result |
|-----------|--------|
| Math engine | `solve("(48/6)+7*2")` → **22**; `solve_in_text("What is (48 / 6) + 7 * 2? Then explain…")` → **22** |
| LLM (combined prompt) | Receives `Known numeric result: 22` in the prompt; explains order of operations at selected level |

**Assessment:** Deterministic math path passes for both pure and mixed prompts. **Sample Prompt 1** in the app UI demonstrates this flow end-to-end.

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

**Measurement environment:** Windows development machine, CPU inference, RAG disabled, TinyLlama Q4_K_M, streaming enabled in benchmark CLI. Reproduce on Ubuntu 22.04 / ADTC Standard Laptop for official comparison.

| Metric | Light tier |
|--------|------------|
| Peak RSS (MB) | **703.0** |
| Tokens/sec (TPS) | **3.67** |
| Time to first token (s) | **1.59** |
| Total latency, 256-token cap (s) | **8.68** |
| Thermal throttle | Not measured in this run |

**Efficiency (S_eff):** `100 × (7168 − 703) / 7168 ≈ 90` — substantial headroom under the 7 GB budget.

**Performance (S_perf):** Relative score depends on audit hardware; rerun `benchmark.py` on the target laptop for comparable TPS.

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
| Explain my mistake (CBC → tutor + RAG) | Shipped |
| Hybrid CBC scoring | Shipped |
| Multi-tier model selector | Shipped |
| Sample demo prompts in UI | Shipped |
| ADTC benchmark CLI (`benchmark.py`) | Shipped |

**Sample curriculum:** `data/cbc_content.json` — Primary / Lower Secondary / Upper Secondary / Technical (e.g. Basic Electricity, Ohm’s Law, Electrical Installation).

**Sample reference PDF:** `data/raw_pdfs/Computer Networks and Data Communication_Lecture 1.pdf`

---

## 8. Future Work

Planned extensions beyond this Gate 1 prototype:

- Scenario generation from ingested PDFs with teacher review
- Persistent progress tracking and teacher reporting
- Swahili and additional local-language UI
- One-click lab installer and pre-built RAG index for school deployment
- Full ADTC profiler run on Ubuntu 22.04 standard hardware

---

## 9. African Context & Bonus Claims

| Claim | Status | Evidence |
|-------|--------|----------|
| **African Use Case** | Qualifies | Offline school lab design; CBC scenario pedagogy; low-cost hardware target |
| **Budget Profile (+10%)** | Qualifies | Light tier ~637 MB file; peak RSS 703.0 MB measured; CPU-only default |
| **African Alpha (+15%)** | Not claimed | English UI today; local-language support in future release |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OOM on 8 GB with 7B + RAG | Audit on Light tier; lazy RAG load; RAG optional |
| Small-model answer quality | RAG grounding; compliance retry; Standard tier where RAM allows |
| Borderline CBC grading | Hybrid keyword + LLM rubric; Explain my mistake loop |
| Missing RAG index | Clear UI warning; `python -m ingestion.ingest_pdf` (fixed package import) |
| Native inference crash (Windows) | Thread cap, lower `n_batch`, RAG unload before LLM, safe-mode retry |
| Thermal throttling | Light model default; CPU-first inference |

---

## 11. Judge Reproduction Checklist

| Step | Action |
|------|--------|
| 1 | Clone repo at submitted commit hash |
| 2 | `pip install -r requirements.txt` |
| 3 | **`bash download_model.sh`** — fetches `model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` |
| 4 | `streamlit run app.py` — Mode: **Offline**, Model: **Light** |
| 5 | Try sample prompts; open **CBC-Learn**; test **Explain my mistake** |
| 6 | Optional RAG: add PDFs → `python -m ingestion.ingest_pdf` → enable RAG checkbox |
| 7 | `python benchmark.py --tier light` for telemetry output |
| 8 | Optional: `adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy` |

**Before DevPost submit:** replace `FILL_TEAM_ID_FROM_ADTF_PORTAL` in `metadata.json`.

**Model manifest:** `models/MODEL_MANIFEST.json` · **Full instructions:** `models/README.md`

**Demo video and screenshots:** Offline Light-tier chat, CBC-Learn, Explain my mistake, and optional RAG (submitted via DevPost).

---

## 12. References

- [Africa Deep Tech Challenge 2026](https://africadeeptech.org/challenge-2026)
- [ADTC 2026 submission template](https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template)
- [ADTC profiler](https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler)
- llama.cpp / GGUF — required ADTC runtime format
- Kenya Competency-Based Curriculum (CBC) — pedagogical alignment for scenario questions

---

*Arapai — Offline AI that Africa can own, run, and trust.*
