import gc
import os
import sys
import threading
import time

from llama_cpp import Llama

from backend.memory_utils import log_memory_usage, reset_peak_rss

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ADTC_MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
ADTC_MODEL_PATH = os.path.join(_PROJECT_ROOT, "model", ADTC_MODEL_FILE)

TIER_PATHS = {
    "light": os.path.join(_PROJECT_ROOT, "models", "lite", "model.gguf"),
    "standard": os.path.join(_PROJECT_ROOT, "models", "standard", "model.gguf"),
    "advanced": os.path.join(_PROJECT_ROOT, "models", "advanced", "model.gguf"),
}


def _resolve_light_model_path():
    """Prefer app path; fall back to ADTC template path (model/*.gguf)."""
    lite = TIER_PATHS["light"]
    if os.path.exists(lite):
        return lite
    if os.path.exists(ADTC_MODEL_PATH):
        return ADTC_MODEL_PATH
    return lite


TIER_BATCH = {
    "light": 128,
    "standard": 256,
    "advanced": 384,
}

DEFAULT_MAX_TOKENS = 256
INFERENCE_DEFAULTS = {
    "temperature": 0.6,
    "top_p": 0.9,
    "stop": ["User:", "Assistant:"],
}

_llm = None
_current_path = None
_current_tier = None
_ready = False
_lock = threading.RLock()
_safe_mode = False


def _thread_count():
    cores = os.cpu_count() or 4
    if sys.platform == "win32":
        return min(4, cores)
    return min(8, cores)


def get_model_path(override=None):
    tier = (override or "light").lower()
    if tier not in TIER_PATHS:
        raise RuntimeError(f"Invalid model tier '{override}'. Choose light, standard, or advanced.")

    path = _resolve_light_model_path() if tier == "light" else TIER_PATHS[tier]
    if not os.path.exists(path):
        raise RuntimeError(
            f"Selected model tier '{tier}' is missing: '{path}'. "
            "Run: bash download_model.sh  (or: python scripts/download_models.py)"
        )
    return path, tier


def _make_llama(model_path, tier, *, safe_mode=False):
    n_threads = 1 if safe_mode else _thread_count()
    n_batch = 64 if safe_mode else TIER_BATCH.get(tier, 128)
    use_gpu = os.environ.get("ARAPAI_GPU", "").strip() in ("1", "true", "yes")
    n_gpu_layers = -1 if use_gpu else 0

    common = dict(
        model_path=model_path,
        n_ctx=2048,
        n_threads=n_threads,
        n_batch=n_batch,
        use_mmap=not safe_mode,
        use_mlock=False,
        verbose=False,
        n_gpu_layers=n_gpu_layers,
    )

    if sys.platform != "win32" and not safe_mode:
        common["n_threads_batch"] = n_threads

    try:
        return Llama(**common)
    except TypeError:
        common.pop("n_threads_batch", None)
        return Llama(**common)


def _ensure_llm(model_tier=None, *, safe_mode=False):
    global _llm, _current_path, _current_tier, _ready, _safe_mode
    path, tier = get_model_path(model_tier)
    reload_needed = (
        _llm is None
        or path != _current_path
        or safe_mode != _safe_mode
    )
    if reload_needed:
        old_llm = _llm
        _llm = _make_llama(path, tier, safe_mode=safe_mode)
        _current_path = path
        _current_tier = tier
        _safe_mode = safe_mode
        _ready = False
        if old_llm is not None:
            del old_llm
            gc.collect()
        log_memory_usage(f"model_loaded_{tier}")
    return _llm


def unload_llm():
    """Release the local model to recover from native inference crashes."""
    global _llm, _current_path, _current_tier, _ready, _safe_mode
    with _lock:
        if _llm is not None:
            del _llm
        _llm = None
        _current_path = None
        _current_tier = None
        _ready = False
        _safe_mode = False
        gc.collect()
        log_memory_usage("model_unloaded")


def get_llm(model_tier=None):
    with _lock:
        return _ensure_llm(model_tier)


def warm_up(model_tier=None):
    global _ready
    with _lock:
        if _ready:
            return
        llm = _ensure_llm(model_tier)
        llm("Say OK.", max_tokens=2, **{k: v for k, v in INFERENCE_DEFAULTS.items() if k != "stop"})
        _ready = True
        log_memory_usage("warm_up")


def _is_native_crash(exc):
    text = str(exc).lower()
    return isinstance(exc, OSError) and (
        "access violation" in text or "exception:" in text
    )


def _run_inference(prompt, max_tokens=DEFAULT_MAX_TOKENS, model_tier=None, stream=False, safe_mode=False):
    with _lock:
        if safe_mode:
            _ensure_llm(model_tier, safe_mode=True)
        else:
            warm_up(model_tier)
        llm = _ensure_llm(model_tier, safe_mode=safe_mode)
        return llm(
            prompt,
            max_tokens=max_tokens,
            stream=stream,
            **INFERENCE_DEFAULTS,
        )


def generate(prompt, max_tokens=DEFAULT_MAX_TOKENS, model_tier=None):
    try:
        result = _run_inference(prompt, max_tokens=max_tokens, model_tier=model_tier, stream=False)
    except OSError as exc:
        if not _is_native_crash(exc):
            raise
        unload_llm()
        result = _run_inference(
            prompt,
            max_tokens=max_tokens,
            model_tier=model_tier,
            stream=False,
            safe_mode=True,
        )

    choices = result.get("choices")
    if not choices:
        return ""
    return (choices[0].get("text") or "").strip()


def generate_stream(prompt, max_tokens=DEFAULT_MAX_TOKENS, model_tier=None):
    try:
        stream = _run_inference(prompt, max_tokens=max_tokens, model_tier=model_tier, stream=True)
    except OSError as exc:
        if not _is_native_crash(exc):
            raise
        unload_llm()
        stream = _run_inference(
            prompt,
            max_tokens=max_tokens,
            model_tier=model_tier,
            stream=True,
            safe_mode=True,
        )

    for chunk in stream:
        choices = chunk.get("choices")
        if not choices:
            continue
        text = choices[0].get("text") or ""
        if text:
            yield text


def benchmark_inference(
    prompt=None,
    max_tokens=DEFAULT_MAX_TOKENS,
    model_tier="light",
    stream=True,
):
    """
    Measure TTFT, tokens/sec, peak RSS, and total latency.
    Returns a dict suitable for REPORT.md and ADTC profiling.
    """
    prompt = prompt or (
        "User: Explain why a longer wire can make a bulb dimmer.\nAssistant:"
    )
    reset_peak_rss()
    log_memory_usage("benchmark_start")

    warm_up(model_tier)
    log_memory_usage("benchmark_after_warmup")

    t0 = time.perf_counter()
    ttft = None
    tokens = 0
    text = ""

    if stream:
        for chunk in generate_stream(prompt, max_tokens=max_tokens, model_tier=model_tier):
            if ttft is None:
                ttft = time.perf_counter() - t0
            text += chunk
            tokens += len(chunk.split())
        if ttft is None:
            ttft = time.perf_counter() - t0
    else:
        text = generate(prompt, max_tokens=max_tokens, model_tier=model_tier)
        tokens = len(text.split())
        ttft = time.perf_counter() - t0

    total = time.perf_counter() - t0
    gen_time = max(total - (ttft or 0), 1e-6)
    gen_tokens = max(tokens - (1 if ttft and ttft < total else 0), 1)
    tps = gen_tokens / gen_time if stream else tokens / max(total, 1e-6)

    mem = log_memory_usage("benchmark_end")
    return {
        "model_tier": model_tier,
        "max_tokens": max_tokens,
        "time_to_first_token_s": round(ttft or 0, 3),
        "total_latency_s": round(total, 3),
        "tokens_approx": tokens,
        "tokens_per_sec": round(tps, 2),
        "peak_rss_mb": mem["peak_rss_mb"],
        "rss_mb": mem["rss_mb"],
        "sample_output_chars": len(text),
    }
