"""Tutor reply validation and regeneration (Streamlit-free core logic)."""
import re

BANNED_PHRASES = (
    "i apologize",
    "sorry",
    "apologies",
    "as mentioned",
    "as i mentioned",
    "earlier response",
    "previous response",
    "confusion earlier",
    "new opportunity",
    "accurate and comprehensive explanation",
    "let me provide",
    "i can provide",
    "i am arapai",
    "arapai is",
    "offline assistant",
    "research assistant",
    "as an ai",
    "as a language model",
    "capabilities",
    "resources",
    "services",
)


def word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def sentence_count(text):
    return len([p for p in re.split(r"[.!?]+", text or "") if p.strip()])


def numbered_steps_count(text):
    return len(re.findall(r"(?m)^\s*\d+[.)]\s+\S+", text or ""))


def is_meta_response(text):
    lower_text = (text or "").lower()
    if not lower_text.strip():
        return True
    return any(phrase in lower_text for phrase in BANNED_PHRASES)


def is_level_compliant(level, text):
    words = word_count(text)
    steps = numbered_steps_count(text)
    if is_meta_response(text):
        return False
    if words < 8:
        return False
    sents = sentence_count(text)
    if level == "basic":
        return 1 <= sents <= 2 and words <= 60 and steps == 0
    if level == "lower_secondary":
        return 1 <= sents <= 5 and 10 <= words <= 220 and steps == 0
    if level == "upper_secondary":
        return 30 <= words <= 380
    if level == "technical":
        return words >= 60
    return True


def ensure_valid_reply(prompt, level, model_tier, reply, generate_fn):
    debug = {
        "selected_level": level,
        "initial_compliant": False,
        "retry_used": False,
        "retry_compliant": False,
        "final_compliant": False,
        "result_source": "none",
        "initial_words": 0,
        "initial_sentences": 0,
        "initial_steps": 0,
        "retry_words": 0,
        "retry_sentences": 0,
        "retry_steps": 0,
    }
    reply = (reply or "").strip()
    debug["initial_words"] = word_count(reply)
    debug["initial_sentences"] = sentence_count(reply)
    debug["initial_steps"] = numbered_steps_count(reply)
    debug["initial_compliant"] = bool(reply and is_level_compliant(level, reply))
    if debug["initial_compliant"]:
        debug["final_compliant"] = True
        debug["result_source"] = "initial"
        return reply, debug

    compliance_hint = (
        "\n\nIMPORTANT RETRY RULE:\n"
        f"Your previous answer did not satisfy level='{level}'. "
        "Regenerate and strictly follow all response rules, including format and length. "
        "Do not apologize and do not reference previous answers. "
        "Answer only the user's latest question directly."
    )
    debug["retry_used"] = True
    retry = generate_fn(prompt + compliance_hint, model_tier=model_tier).strip()
    debug["retry_words"] = word_count(retry)
    debug["retry_sentences"] = sentence_count(retry)
    debug["retry_steps"] = numbered_steps_count(retry)
    debug["retry_compliant"] = bool(retry and is_level_compliant(level, retry))
    if debug["retry_compliant"]:
        debug["final_compliant"] = True
        debug["result_source"] = "retry"
        return retry, debug

    if retry and not is_meta_response(retry):
        debug["final_compliant"] = False
        debug["result_source"] = "retry_noncompliant"
        return retry, debug
    if reply and not is_meta_response(reply):
        debug["final_compliant"] = False
        debug["result_source"] = "initial_noncompliant"
        return reply, debug

    final = generate_fn(
        prompt
        + "\n\nFINAL RETRY RULE:\n"
        + "Answer the latest user question directly at the selected level. "
        + "No apology, no meta commentary. Explain the topic only.",
        model_tier=model_tier,
    ).strip()
    if final:
        debug["final_compliant"] = is_level_compliant(level, final)
        debug["result_source"] = "final_retry"
        return final, debug
    debug["final_compliant"] = False
    debug["result_source"] = "hard_fallback"
    return "I could not generate a valid explanation. Please ask again.", debug
