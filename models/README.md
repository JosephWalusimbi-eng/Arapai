# LLM models (GGUF)

Arapai requires **GGUF weights via llama.cpp**. Weights are **not committed to Git** (hundreds of MB to several GB). Download them once using the instructions below.

---

## Quick start (Light tier)

**Minimum to run the default offline path:** the **Light** tier model only (~637 MB).

From project root:

```bash
bash download_model.sh
```

This saves the weight file at **`model/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`** (matches `metadata.json` → `_runtime.model_path`) and copies it to `models/lite/model.gguf` for the Streamlit app.

**Windows alternative:**

```bash
python scripts/download_models.py
```

Then verify and run:

```bash
python benchmark.py --tier light
streamlit run app.py
```

**Recommended settings:** Mode = **Offline**, Model = **Light**.

### Manual download (if the script fails)

Direct URL (no Hugging Face account required for this public file):

```
https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

Save the file as **`models/lite/model.gguf`** (exact filename required by `backend/llm_engine.py`).

### Machine-readable manifest

Full URLs and paths for all tiers: **`models/MODEL_MANIFEST.json`**

---

## All model tiers

Put **one** file named **`model.gguf`** in the matching folder:

| Folder | File | When used | Approx. size |
|--------|------|-----------|--------------|
| `models/lite/` | `model.gguf` | Any RAM; **default for low-RAM labs** | ~637 MB |
| `models/standard/` | `model.gguf` | 4+ GB free RAM | ~3.9 GB |
| `models/advanced/` | `model.gguf` | 8+ GB free RAM | ~4.1 GB |

### Download script

```bash
python scripts/download_models.py              # light only
python scripts/download_models.py --tier standard
python scripts/download_models.py --tier advanced
python scripts/download_models.py --tier all
```

### Direct download links

**Lite (default)** — TinyLlama 1.1B Chat Q4_K_M  
https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf  
→ `models/lite/model.gguf`

**Standard** — Llama-2 7B Chat Q4_K_M (compatible with pinned llama-cpp-python 0.2.20)  
https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf  
→ `models/standard/model.gguf`

**Advanced** — Mistral 7B Instruct v0.2 Q4_K_M  
https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf  
→ `models/advanced/model.gguf`

> Prefer **Q4_K_M** quantizations for speed and RAM efficiency on typical 8 GB school laptops.

---

## Why models are not in Git

| Reason | Detail |
|--------|--------|
| Size | Lite ~637 MB; Standard/Advanced ~4 GB each |
| GitHub limits | Large binaries bloat the repo and hit LFS quotas |
| Deployment | Operators fetch weights at install time from documented URLs |
| Reproducibility | Pinned URLs in `MODEL_MANIFEST.json` match the submitted commit |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Selected model tier 'light' is missing` | Run `python scripts/download_models.py` |
| Wrong filename | Must be exactly `model.gguf` inside the tier folder |
| Advanced tier crashes | Use **Light** or **Standard** in the Model menu |

Run the app from project root: `streamlit run app.py`
