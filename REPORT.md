# Arapai — ADTC 2026 Submission Report

**Project:** Arapai (Offline AI Education Tutor)  
**Challenge:** [Africa Deep Tech Challenge 2026 — The Laptop LLM Challenge](https://africadeeptech.org/challenge-2026)  
**Problem domain:** Math & Scientific Reasoning (education tutoring)  
**Submission gate:** Gate 1 — Submission Package (deadline: 24 July 2026)  
**Repository:** Open-source; run from project root with `streamlit run app.py`

---

## 1. Executive Summary

**Arapai** is an offline-first educational assistant designed for schools and learners who cannot rely on cloud APIs, stable fibre, or sustained electricity. It runs entirely on a standard laptop using **GGUF models via llama.cpp** (`llama-cpp-python`), optional **RAG over local curriculum PDFs**, **safe numeric math evaluation**, and a **Competency-Based Curriculum (CBC) scenario quiz** aligned with African classroom realities.

This Gate 1 submission presents a **working prototype as it exists today**: a functional on-device tutor with curriculum-grounded practice and a first integration between assessment and explanation (“Explain my mistake”). The report also documents a **three-phase roadmap** toward curriculum-native generation, teacher tooling, and school-scale deployment—without claiming those future features as already shipped.

**Cross-disciplinary integration (load-bearing):**

| Discipline | Role in Arapai |
|------------|----------------|
| On-device LLM inference | Core tutor: leveled explanations, streaming responses |
| Information retrieval (RAG) | FAISS + sentence embeddings over ingested PDF notes |
| Structured assessment | CBC scenario questions with rubric-based scoring |
| Symbolic/numeric reasoning | Safe math engine for arithmetic without `eval()` |

**African context:** Built for offline school labs, CBC-style scenario learning, and deployment on low-cost refurbished hardware ($150–$500). Primary UI language is English; roadmap includes Swahili and other local languages (African Alpha Bonus target in Phase 2).

---

## 2. Problem Definition

### 2.1 The problem

Across Africa, students and teachers face a recurring gap:

1. **Access economics** — Cloud LLMs require API fees, reliable internet, and continuous power. Many schools have none of these during normal teaching hours.
2. **Generic AI is not curriculum-aligned** — Chatbots answer broadly but do not practice CBC-style *scenario reasoning* (“A pupil connects a bulb but it does not light—explain why”) or tie answers to local course materials.
3. **One-size-fits-all explanations** — Learners at Primary, Lower Secondary, Upper Secondary, and Technical levels need different depth; a single answer frustrates both beginners and advanced students.
4. **Assessment without teaching** — Quizzes that only mark right/wrong do not close the learning loop when a student misunderstands a concept.

### 2.2 Target users

| User | Need |
|------|------|
| **Student** | Practice scenarios, ask questions offline, get explanations at their level |
| **Teacher** | Supplement lessons with an offline tutor grounded in uploaded PDFs |
| **School IT / lab admin** | Deploy once on many identical laptops without cloud dependency |

### 2.3 Success criteria (product)

- Runs **100% offline** during ADTC audit (no network calls for inference).
- Stays **within the 7 GB RAM ceiling** on the ADTC Standard Laptop.
- Delivers **scientifically structured explanations** at selectable depth levels.
- Connects **practice → feedback → explanation** in one session.
- Grounds answers in **local documents** when RAG is enabled.

---

## 3. Constraints

### 3.1 ADTC hardware and scoring constraints

| Constraint | Requirement | Arapai response |
|------------|-------------|-----------------|
| **RAM ceiling** | Peak RSS ≤ 7 GB; OOM → disqualification | Default audit config uses **Light tier** (~637 MB GGUF) |
| **Hardware profile** | 8 GB DDR4, integrated GPU, Ubuntu 22.04 | CPU inference via llama.cpp; optional CUDA not required for audit |
| **Runtime** | 100% offline during testing | Offline mode is the submission path; Online mode is dev-only comparison |
| **Model format** | GGUF via llama.cpp only | All tiers use `models/*/model.gguf` |
| **Scoring** | S_total = 0.50·S_acc + 0.30·S_perf + 0.20·S_eff − P_thermal | Optimise for accuracy, tokens/sec, and low peak RAM |

### 3.2 Operational constraints (African schools)

- **Intermittent power and no fibre** — Full offline operation after one-time setup.
- **Identical lab machines** — Pinned `requirements.txt`; no `pip install -U` in production.
- **Non-technical operators** — Single command install; Streamlit UI; model tier selector defaults to Light.
- **Large model files not in Git** — GGUF weights downloaded separately (see `models/README.md`).

### 3.3 Technical constraints (self-imposed)

- **Python 3.10 / 3.11** — Pinned stack; avoid 3.12 llama-cpp build issues.
- **Context window 2048 tokens** — Fits standard laptop memory; limits very long RAG injection.
- **No arbitrary code execution** — Math limited to whitelisted numeric grammar.
- **Single LLM loaded at a time** — Tier switch reloads model to bound memory.

---

## 4. Design Decisions

### 4.1 Offline-first, cloud-optional

**Decision:** Primary product path is local GGUF inference. An optional Online (Gemma 1.1) mode exists for developer comparison only; it is **disabled for ADTC audit**.

**Rationale:** Matches ADTC mandate and African school reality. Cloud is a benchmark, not a dependency.

### 4.2 Three model tiers (manual selection)

| Tier | Typical model | Quant | Approx. file size | Intended RAM |
|------|---------------|-------|-------------------|--------------|
| **Light** | TinyLlama 1.1B Chat | Q4_K_M | ~637 MB | Any (audit default) |
| **Standard** | Llama-2 7B Chat | Q4_K_M | ~3.8 GB | 4+ GB free |
| **Advanced** | Mistral 7B Instruct v0.2 | Q4_K_M | ~4.1 GB | 8 GB (risky with RAG stack) |

**Decision:** User selects tier manually; default is Light.

**Rationale:** Lab machines vary. Automatic tier detection was rejected to keep behaviour predictable for IT staff and to avoid OOM on the 7 GB budget when RAG embeddings are loaded.

**ADTC submission recommendation:** Ship and benchmark **`models/lite/model.gguf`** (TinyLlama Q4_K_M).

### 4.3 Four explanation levels with compliance checking

Levels: `basic`, `lower_secondary`, `upper_secondary`, `technical`.

**Decision:** Prompt rules enforce length, jargon, and structure per level. `_is_level_compliant()` validates output; non-compliant replies trigger a regeneration pass.

**Rationale:** Education requires *pedagogical* control, not just raw fluency. Rule-based validation is cheap on CPU and improves consistency on small models.

### 4.4 RAG over local PDFs (cross-disciplinary core)

**Pipeline:**

1. PDFs placed in `data/raw_pdfs/`
2. `python -m ingestion.ingest_pdf` → chunk (500 chars, 50 overlap) → embed (`all-MiniLM-L6-v2`) → FAISS index
3. At query time, top-3 chunks injected as “Reference Material” in the prompt

**Decision:** RAG is optional (checkbox). Embedding model loads only when RAG is used.

**Rationale:** Teachers upload *their* notes; the LLM becomes curriculum-aware without fine-tuning. This is the load-bearing deep-tech pairing: **generative model + local retrieval**.

### 4.5 CBC Learning Mode + “Explain my mistake”

**Decision:** Scenario questions live in static JSON (`data/cbc_content.json`). After submit:

- Correct → feedback + “Next question”
- Wrong / partial → **“Explain my mistake”** calls the same tutor pipeline (level + RAG + compliance)

**Rationale:** Closes the learning loop without waiting for dynamic question generation (Phase 2). Uses existing prompt and level infrastructure.

**Trade-off acknowledged:** Answer checking uses keyword overlap (`check_answer()`), not semantic grading. Phase 1 roadmap replaces this with LLM-assisted rubric scoring.

### 4.6 Safe math engine (no `eval()`)

**Decision:** Numeric expressions matching `[\d\s+\-*/().]+` are parsed and evaluated with a small recursive-descent evaluator.

**Rationale:** Students ask “what is (12 + 4) * 3?” — instant, deterministic, zero hallucination risk, zero code-injection risk.

### 4.7 Streamlit monolith (current) vs modular split (planned)

**Decision (current):** Single `app.py` for Gate 1 velocity.

**Planned (Phase 1):** Split into `backend/cbc_engine.py`, `backend/tutor_engine.py`, and UI pages.

**Rationale:** Ship working prototype first; refactor before teacher dashboard and generation pipeline.

---

## 5. Tools & Technology Stack

### 5.1 Core stack

| Component | Tool / version | Purpose |
|-----------|----------------|---------|
| UI | Streamlit 1.31.1 | Chat + CBC modes, streaming display |
| LLM runtime | llama-cpp-python 0.2.20 | GGUF inference (llama.cpp) |
| Model weights | GGUF (Q4_K_M / Q5_K_M) | Quantized on-device models |
| RAG embeddings | sentence-transformers 2.6.1 | `all-MiniLM-L6-v2` |
| Vector index | faiss-cpu | Top-k chunk retrieval |
| PDF parsing | pypdf | Curriculum ingestion |
| Numerics | numpy, psutil | Arrays, optional RAM introspection |

### 5.2 Repository layout

```
app.py                  # Streamlit entry (chat + CBC-Learn)
backend/
  llm_engine.py         # Model load, generate, stream
  prompt_builder.py     # Level-aware prompts
  rag_engine.py         # FAISS retrieval
  math_engine.py        # Safe arithmetic
  explanation_levels.py # Schema validation utilities
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

### 5.3 Reproduction (Gate 1)

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux:   source venv/bin/activate
pip install -r requirements.txt

# Download TinyLlama Q4_K_M → models/lite/model.gguf  (see models/README.md)

# Optional RAG:
#   Place PDFs in data/raw_pdfs/
#   python -m ingestion.ingest_pdf

streamlit run app.py
```

**Audit configuration:** Mode = **Offline**, Model = **Light**, RAG = optional (pre-build index before demo).

---

## 6. Benchmarks & Evaluation

### 6.1 ADTC scoring model (target)

```
S_total = 0.50 × S_acc + 0.30 × S_perf + 0.20 × S_eff − P_thermal
```

| Metric | Weight | Measurement | Arapai strategy |
|--------|--------|-------------|-----------------|
| **S_acc** | 50% | Panel + prompt benchmarks | Strong domain prompts; RAG grounding; level compliance |
| **S_perf** | 30% | Tokens/sec vs max | Light model; streaming UX; `n_threads = cpu_count` |
| **S_eff** | 20% | `(7 GB − peak RAM) / 7 GB` | TinyLlama tier; lazy RAG load; single model instance |
| **P_thermal** | −10 | Core temp > 85°C | CPU-only light model reduces throttle risk |

**Profiling tool:** [ADTC open-source profiler](https://africadeeptech.org/challenge-2026) — to be run on Ubuntu 22.04 / 8 GB hardware before Gate 2 audit; results appended to this section.

### 6.2 Recommended audit configuration

| Setting | Value |
|---------|-------|
| OS | Ubuntu 22.04 LTS |
| Model file | `models/lite/model.gguf` (TinyLlama 1.1B Chat Q4_K_M) |
| Mode | Offline |
| `n_ctx` | 2048 |
| `max_tokens` | 256 (default generation cap) |
| RAG | Off for pure LLM telemetry; On for accuracy demo |

> **Note:** Standard (7B) and Advanced tiers may exceed the 7 GB peak-RSS budget when combined with Streamlit, sentence-transformers, and OS overhead. Gate 1 demonstrates tier flexibility; Gate 2 audit should use **Light** unless profiling proves otherwise.

### 6.3 Submission test prompts (domain benchmarks)

Per ADTC rules, the team submits two prompts; organisers add two hidden prompts. Below are Arapai’s Gate 1 prompts for the **Math & Scientific Reasoning / Education** track.

#### Prompt A — Scientific reasoning (Ohm’s Law scenario)

**User prompt:**

> A student connects a thin, long wire in a circuit and notices the bulb is dimmer than when using a short, thick wire. Explain why this happens.

**Expected qualities (S_acc rubric):**

- Identifies resistance depends on length and cross-sectional area
- Connects lower current to dimmer bulb
- At `basic` level: 1–2 simple sentences, no jargon
- At `technical` level: numbered steps, correct terminology (resistance, current, Ohm’s law)

#### Prompt B — Quantitative reasoning (safe math + concept)

**User prompt:**

> What is (48 / 6) + 7 * 2? Then explain in one sentence what order of operations means.

**Expected qualities:**

- Math engine returns `26.0` deterministically (no LLM required for arithmetic)
- LLM explains order of operations at selected explanation level
- No meta-commentary or self-description (compliance rules)

### 6.4 Internal functional benchmarks (current prototype)

These validate product behaviour today; they are not substitutes for ADTC telemetry.

| Test | Method | Pass criteria |
|------|--------|---------------|
| Offline inference | Run with network disabled | Chat and CBC explain work |
| Level compliance | `_is_level_compliant()` on sample outputs | Basic ≤ 2 sentences; technical includes steps |
| Math safety | `math_engine.solve("import os")` | Returns `None` (rejected) |
| Math correctness | `solve("(48/6)+7*2")` | Returns `26.0` |
| RAG retrieval | Ingest sample PDF; query related term | Non-empty reference material in prompt |
| CBC loop | Wrong answer → Explain my mistake | Tutor explanation at selected level |
| Memory discipline | Light model + chat only | Peak RSS target < 5 GB on 8 GB machine (team to confirm via profiler) |

### 6.5 Benchmark results (to be completed pre–Gate 2)

| Metric | Light tier | Standard tier | Notes |
|--------|------------|---------------|-------|
| Peak RSS (MB) | _TBD_ | _TBD_ | Run ADTC profiler |
| Tokens/sec (TPS) | _TBD_ | _TBD_ | 256-token generation |
| Time to first token | _TBD_ | _TBD_ | Streaming chat |
| Thermal throttle | _TBD_ | _TBD_ | 10+ min sustained run |

---

## 7. Current Deliverable (Gate 1 Snapshot)

What is **working and included** in this submission:

| Feature | Status |
|---------|--------|
| Offline GGUF chat tutor | ✅ Shipped |
| Four explanation levels + compliance retry | ✅ Shipped |
| Token streaming (offline) | ✅ Shipped |
| Safe numeric math | ✅ Shipped |
| RAG over local PDFs | ✅ Shipped (requires ingestion step) |
| CBC scenario quiz (static bank) | ✅ Shipped |
| Explain my mistake (CBC → tutor + RAG) | ✅ Shipped |
| Multi-tier model selector | ✅ Shipped |
| Warm light/dark UI themes | ✅ Shipped |
| Online comparison mode (Gemma API) | ⚠️ Dev only — **not for audit** |

**Sample curriculum content:** `data/cbc_content.json` — Primary / Lower Secondary / Upper Secondary / Technical topics (e.g. Basic Electricity, Ohm’s Law, Electrical Installation).

**Sample reference document:** `data/raw_pdfs/Computer Networks and Data Communication_Lecture 1.pdf`

---

## 8. Roadmap — Where We Are Going

The Gate 1 prototype is intentionally scoped. The following phases describe the path to a school-ready product without overstating current capabilities.

### Phase 1 — Unify & harden (target: post–Gate 1, pre–Gate 2)

| Item | Outcome |
|------|---------|
| Connect CBC ↔ tutor (extend) | Richer mistake context; show correct concepts after explanation |
| Improve `check_answer()` | Keyword match + LLM rubric for fair partial credit |
| Refactor `app.py` | Modular backend + UI for testability |
| RAG index shipping | Pre-built index or one-click ingest script in installer |
| Secrets hygiene | Remove tokens from docs; env-var only |
| ADTC profiler runs | Fill Section 6.5 with measured TPS, RSS, thermal |

### Phase 2 — Curriculum-native (1–2 months)

| Item | Outcome |
|------|---------|
| Scenario generation from PDFs | LLM + RAG draft CBC questions from ingested notes |
| Teacher approval workflow | Review → edit → publish to question bank |
| Progress persistence | Per-topic scores survive session refresh (local JSON/SQLite) |
| Swahili / local language UI | African Alpha Bonus; bilingual explanations |
| Content schema | Validated JSON (topic, outcome, scenario, rubric) |

### Phase 3 — School-ready scale (ongoing)

| Item | Outcome |
|------|---------|
| One-click lab installer | venv + deps + model check + health screen |
| Teacher dashboard | Export CSV reports; weak-concept summary |
| Golden eval suite | 20 prompts × 4 levels regression before deployment |
| Classroom mode | Student ID, no cloud accounts |
| Pilot partnerships | School labs in target regions |

**North-star product loop (Phase 2+):**

```
Curriculum PDF → ingest → RAG
                ↓
         Scenario practice (CBC)
                ↓
         Wrong answer → Explain my mistake (leveled tutor)
                ↓
         Teacher review & progress report
```

---

## 9. African Context & Bonus Claims

| Claim | Evidence (today) | Roadmap |
|-------|------------------|---------|
| **African Use Case** | Offline school lab design; CBC scenario pedagogy; low-cost hardware tiers | Teacher pilots, local PDF corpora |
| **African Alpha (+15%)** | English primary; Kenya CBC alignment | Swahili UI + explanations (Phase 2) |
| **Budget laptop** | Light tier ~637 MB model; pinned deps; CPU-first | Profiler-validated < 7 GB peak RSS |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OOM on 8 GB with 7B + RAG | Audit on Light tier; lazy load; RAG optional |
| Small model quality | RAG grounding; compliance retry; tier upgrade where RAM allows |
| Keyword-only CBC grading | Phase 1 LLM rubric; explain-mistake loop already softens failure |
| Empty RAG index | Clear UI warning; ingestion documented in README |
| Thermal throttling | Light model; avoid sustained Advanced tier on audit hardware |

---

## 11. Gate 1 Checklist (DevPost)

| Deliverable | Location / action |
|-------------|-------------------|
| Open-source repo | This repository |
| **REPORT.md** | This file |
| Screenshots / clips | Capture: Chat, CBC-Learn, Explain my mistake, RAG toggle |
| 2-minute video | Pitch + demo on offline Light tier |
| GGUF weights | `models/lite/model.gguf` — linked in README, not in Git |
| Bonus claims | African use case; budget laptop (Light tier) |

---

## 12. References

- [Africa Deep Tech Challenge 2026](https://africadeeptech.org/challenge-2026)
- [ADTC 2026 submission template](https://africadeeptech.org/challenge-2026) (linked from challenge site)
- [ADTC profiler tool](https://africadeeptech.org/challenge-2026) (local benchmarking)
- llama.cpp / GGUF — required ADTC runtime format
- Kenya Competency-Based Curriculum (CBC) — pedagogical alignment for scenario questions

---

*Document version: Gate 1 — June 2026*  
*Arapai — Offline AI that Africa can own, run, and trust.*
