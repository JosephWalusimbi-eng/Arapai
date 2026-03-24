import os
import threading
from llama_cpp import Llama

# Resolve paths relative to project root (not current working directory).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ---------------- MODEL TIERS (manual selection) ----------------
TIER_PATHS = {
    "light": os.path.join(_PROJECT_ROOT, "models", "lite", "model.gguf"),
    "standard": os.path.join(_PROJECT_ROOT, "models", "standard", "model.gguf"),
    "advanced": os.path.join(_PROJECT_ROOT, "models", "advanced", "model.gguf"),
}

def get_model_path(override=None):
    """
    Return model path for explicit tier selection.
    - override in {'light','standard','advanced'}: require that tier's file.
    - override is None: default to light tier.
    """
    tier = (override or "light").lower()
    if tier not in TIER_PATHS:
        raise RuntimeError(f"Invalid model tier '{override}'. Choose light, standard, or advanced.")

    path = TIER_PATHS[tier]
    if not os.path.exists(path):
        raise RuntimeError(
            f"Selected model tier '{tier}' is missing: '{path}'. "
            "Place a GGUF file there named model.gguf."
        )
    return path

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
                try:
                    return Llama(**c, n_gpu_layers=n_gpu_layers, use_mlock=use_mlock)
                except AssertionError as e:
                    raise RuntimeError(
                        f"Failed to load GGUF model at '{model_path}'. "
                        "The file may be missing, corrupt, or incompatible with this llama.cpp build."
                    ) from e
            except AssertionError as e:
                raise RuntimeError(
                    f"Failed to load GGUF model at '{model_path}'. "
                    "The file may be missing, corrupt, or incompatible with this llama.cpp build."
                ) from e
            except Exception:
                continue
    try:
        return Llama(**{k: v for k, v in common.items() if k != "n_threads_batch"}, n_gpu_layers=0, use_mlock=False)
    except AssertionError as e:
        raise RuntimeError(
            f"Failed to load GGUF model at '{model_path}'. "
            "The file may be missing, corrupt, or incompatible with this llama.cpp build."
        ) from e

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

#
# NOTE:
# Do not warm up at import time. Streamlit re-imports modules during reruns,
# and any model-load failure would crash the whole app before the UI can render.
# The UI should call warm_up() explicitly (and handle errors gracefully).

# ---------------- INFERENCE ----------------
def generate(prompt, max_tokens=256, model_tier=None):
    """Generate a response. model_tier: 'light'|'standard'|'advanced' (None defaults to light)."""
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
