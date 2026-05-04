import os
import json
import urllib.request
import urllib.error

# Using Gemma 1.1 7B as it is the most stable Gemma endpoint on the free Inference API.
MODEL_ID = "google/gemma-1.1-7b-it"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

def _get_hf_token():
    return (
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HUGGINGFACE_API_TOKEN")
    )

def generate(prompt, max_tokens=512, temperature=0.7, top_p=0.9):
    """
    Online generation via Hugging Face Inference API.
    """
    token = _get_hf_token()
    if not token:
        raise RuntimeError("HF token missing. Set environment variable HF_TOKEN.")

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_data = resp.read().decode("utf-8")
            data = json.loads(raw_data)

            # The API returns a list of dicts: [{"generated_text": "..."}]
            if isinstance(data, list) and len(data) > 0:
                result = data[0].get("generated_text", "")
                return result.strip()

            # Sometimes it returns a single dict on error or different task
            if isinstance(data, dict):
                if "error" in data:
                    raise RuntimeError(f"HF API Error: {data['error']}")
                return str(data)

            return raw_data
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            # Try to parse JSON error from HF
            err_json = json.loads(error_body)
            msg = err_json.get("error", error_body)
        except:
            msg = error_body or e.reason

        raise RuntimeError(f"Online inference failed ({e.code}): {msg}")
    except Exception as e:
        raise RuntimeError(f"Online inference failed: {e!s}")
