import os
import threading
import psutil
from llama_cpp import Llama

# ---------------- RAM DETECTION ----------------
def get_available_ram_gb():
    return psutil.virtual_memory().available / (1024 ** 3)

# ---------------- MODEL TIERS (manual override) ----------------
# UI uses: "Auto" | "Light" | "Standard" | "Advanced"
TIER_PATHS = {
    "light": "models/lite/model.gguf",
    "standard": "models/standard/model.gguf",
    "advanced": "models/advanced/model.gguf",
}

def _get_auto_model_path():
    """Choose model path from available RAM and existing model files."""
    ram = get_available_ram_gb()

    if ram >= 8 and os.path.exists("models/advanced/model.gguf"):
        print("Using ADVANCED model (auto)")
        return "models/advanced/model.gguf"

    if ram >= 4 and os.path.exists("models/standard/model.gguf"):
        print("Using STANDARD model (auto)")
        return "models/standard/model.gguf"

    if os.path.exists("models/lite/model.gguf"):
        print("Using LITE model (auto)")
        return "models/lite/model.gguf"

    raise RuntimeError(
        "No compatible model found. Place a GGUF model file at one of:\n"
        "  • models/lite/model.gguf (any RAM)\n"
        "  • models/standard/model.gguf (4+ GB free RAM)\n"
        "  • models/advanced/model.gguf (8+ GB free RAM)\n"
        "Download a GGUF model (e.g. TinyLlama, Phi-2, Llama from Hugging Face) and put it in the right folder."
    )

def get_model_path(override=None):
    """
    Return model path: use override if it is 'light'|'standard'|'advanced' and file exists,
    otherwise use auto selection. override=None or 'auto' => auto.
    """
    if override and override != "auto":
        override = override.lower()
        if override in TIER_PATHS and os.path.exists(TIER_PATHS[override]):
            return TIER_PATHS[override]
    return _get_auto_model_path()

# ---------------- LAZY LOAD (supports runtime tier change) ----------------
_llm = None
_current_path = None
_ready = False
_lock = threading.Lock()

def _make_llama(model_path):
    n_threads = os.cpu_count() or 4
    common = dict(
        model_path=model_path,
        n_ctx=2048,
        n_threads=n_threads,
        n_batch=512,
        n_threads_batch=n_threads,  # Ollama-style: use all cores for batch
        use_mmap=True,
        verbose=False,  # less I/O overhead
    )
    # Prefer GPU if available (Ollama-style acceleration)
    for n_gpu_layers in (-1, 0):
        for use_mlock in (True, False):
            try:
                return Llama(**common, n_gpu_layers=n_gpu_layers, use_mlock=use_mlock)
            except TypeError:
                c = {k: v for k, v in common.items() if k != "n_threads_batch"}
                return Llama(**c, n_gpu_layers=n_gpu_layers, use_mlock=use_mlock)
            except Exception:
                continue
    return Llama(**{k: v for k, v in common.items() if k != "n_threads_batch"}, n_gpu_layers=0, use_mlock=False)

def get_llm(model_tier=None):
    """Load or return the current LLM; reload if model_tier implies a different path."""
    global _llm, _current_path
    path = get_model_path(model_tier)
    with _lock:
        if _llm is None or path != _current_path:
            old_llm = _llm
            try:
                new_llm = _make_llama(path)
                _llm = new_llm
                _current_path = path
                if old_llm is not None:
                    del old_llm
            except Exception:
                _llm = old_llm  # leave or restore so _llm is always defined
                raise
        return _llm

def warm_up(model_tier=None):
    """Run a short inference so the model is ready. Uses current or given model_tier."""
    global _ready
    if _ready:
        return
    llm = get_llm(model_tier)
    with _lock:
        if _ready:
            return
        llm("Say OK.", max_tokens=2)
        _ready = True

# Initial warm-up with auto selection (keeps first-run behavior)
warm_up(None)

# ---------------- INFERENCE ----------------
def generate(prompt, max_tokens=256, model_tier=None):
    """Generate a response. model_tier: None/'auto' = auto, or 'light'|'standard'|'advanced'."""
    llm = get_llm(model_tier)
    result = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.6,
        top_p=0.9,
        stop=["User:", "Assistant:"],
    )
    choices = result.get("choices")
    if not choices:
        return ""
    text = choices[0].get("text") or ""
    return text.strip()


def generate_stream(prompt, max_tokens=256, model_tier=None):
    """
    Generate a response token-by-token (Ollama-style streaming).
    Yields text chunks for fast time-to-first-token.
    """
    llm = get_llm(model_tier)
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.6,
        top_p=0.9,
        stop=["User:", "Assistant:"],
        stream=True,
    )
    for chunk in stream:
        choices = chunk.get("choices")
        if not choices:
            continue
        text = choices[0].get("text") or ""
        if text:
            yield text
