import json
import os
import urllib.request
import urllib.error


MODEL_ID = "google/gemma-4-31B-it"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"


def _get_hf_token():
    # Support common env var names
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGINGFACE_API_TOKEN")
    )


def generate(prompt, max_tokens=256, temperature=0.6, top_p=0.9):
    """
    Online generation via Hugging Face Inference API.
    Requires env var HF_TOKEN (or HUGGINGFACEHUB_API_TOKEN).
    """
    token = _get_hf_token()
    if not token:
        raise RuntimeError(
            "HF token missing. Set environment variable HF_TOKEN (or HUGGINGFACEHUB_API_TOKEN) "
            "to use Online mode."
        )

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": int(max_tokens),
            "temperature": float(temperature),
            "top_p": float(top_p),
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"Online inference failed ({e.code}): {body or e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Online inference failed: {e!r}") from e

    try:
        data = json.loads(raw)
    except Exception:
        raise RuntimeError(f"Online inference returned non-JSON: {raw[:500]}")

    # Typical response: [{"generated_text": "..."}]
    if isinstance(data, list) and data:
        item = data[0] if isinstance(data[0], dict) else None
        if item and "generated_text" in item:
            return (item.get("generated_text") or "").strip()

    # Error shapes can be {"error": "..."} or {"estimated_time": ...}
    if isinstance(data, dict):
        if "error" in data:
            raise RuntimeError(f"Online inference error: {data.get('error')}")
        if "message" in data:
            raise RuntimeError(f"Online inference message: {data.get('message')}")

    raise RuntimeError(f"Unexpected online inference response: {str(data)[:500]}")

