import os
import threading
import psutil
from llama_cpp import Llama

# ---------------- RAM DETECTION ----------------
def get_available_ram_gb():
    return psutil.virtual_memory().available / (1024 ** 3)

# ---------------- MODEL SELECTION ----------------
def select_model_path():
    ram = get_available_ram_gb()

    if ram >= 8 and os.path.exists("models/advanced/model.gguf"):
        print("Using ADVANCED model")
        return "models/advanced/model.gguf"

    if ram >= 4 and os.path.exists("models/standard/model.gguf"):
        print("Using STANDARD model")
        return "models/standard/model.gguf"

    if os.path.exists("models/lite/model.gguf"):
        print("Using LITE model")
        return "models/lite/model.gguf"

    raise RuntimeError(
        "No compatible model found. Place a GGUF model file at one of:\n"
        "  • models/lite/model.gguf (any RAM)\n"
        "  • models/standard/model.gguf (4+ GB free RAM)\n"
        "  • models/advanced/model.gguf (8+ GB free RAM)\n"
        "Download a GGUF model (e.g. TinyLlama, Phi-2, Llama from Hugging Face) and put it in the right folder."
    )

MODEL_PATH = select_model_path()

# ---------------- LOAD MODEL ONCE (preload at import) ----------------
def _make_llama():
    common = dict(
        model_path=MODEL_PATH,
        n_ctx=2048,
        n_threads=os.cpu_count() or 4,
        n_batch=512,
        use_mmap=True,
    )
    for n_gpu_layers in (-1, 0):
        for use_mlock in (True, False):
            try:
                return Llama(**common, n_gpu_layers=n_gpu_layers, use_mlock=use_mlock)
            except Exception:
                continue
    return Llama(**common, n_gpu_layers=0, use_mlock=False)

llm = _make_llama()

_ready = False
_lock = threading.Lock()

def warm_up():
    global _ready
    with _lock:
        if not _ready:
            llm("Say OK.", max_tokens=2)
            _ready = True

warm_up()

# ---------------- INFERENCE ----------------
def generate(prompt, max_tokens=256):
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
