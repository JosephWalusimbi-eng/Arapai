# Technical Report - Arapai: Offline AI Education Tutor

**Team ID:** Perry
**Domain:** math_scientific_reasoning
**Model:** TinyLlama-1.1B-Chat-Q4_K_M

---

## Problem

Students in many parts of Uganda and East Africa lack reliable access to internet-based learning tools. In areas like Arapai (Soroti District), poor connectivity makes cloud-based AI tutors impractical.

At the same time, existing AI systems are not aligned with local curricula and do not support structured learning approaches such as competency-based education.

Arapai addresses this by providing an **offline AI tutor** that runs on standard laptops, enabling students to ask questions, practice scenario-based problems, and receive explanations without requiring internet access.

---

## Design Decisions

* **Base model:**

  * TinyLlama 1.1B Chat for lightweight offline tutoring

* **Quantization:**

  * Q4_K_M chosen to balance performance and memory usage within 8GB RAM constraints

* **Architecture choice:**

  * Single GGUF LLM for tutoring
  * Optional RAG system over local PDFs for curriculum grounding
  * Deterministic math engine for reliable arithmetic

* **Alternatives considered:**

  * Larger models rejected due to memory constraints
  * Cloud-based APIs rejected due to connectivity and cost
  * Pure chatbot systems rejected for lack of structured learning support

---

## Constraints

* Target: **8 GB RAM**, integrated GPU, Ubuntu-compatible systems
* CPU-only inference using llama.cpp
* Fully offline operation (no cloud or API dependency)
* Designed for low-connectivity school environments
* Supports curriculum-based learning with local materials

---

## Benchmarks

| Metric              | Value                                                |
| ------------------- | ---------------------------------------------------- |
| Machine             | HP EliteBook (Intel Core i5, 8GB RAM, 256GB storage) |
| RAM at peak         | ~703 MB                                              |
| Time to first token | ~1.6 s                                               |
| Generation speed    | ~3.6 tokens/sec                                      |
| Thermal throttling  | None observed                                        |

These are self-reported development benchmarks. Official scores are measured by the ADTC profiler on the standard evaluation machine.
