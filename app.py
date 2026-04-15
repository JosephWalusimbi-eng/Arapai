import re
import streamlit as st
from backend.llm_engine import warm_up, generate, generate_stream
from backend.math_engine import solve
from backend.prompt_builder import (
    LEVEL_HINTS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    LEVELS,
    build_prompt,
)
from backend.rag_engine import retrieve

st.set_page_config(page_title="Arapai", layout="wide")


def _inject_gemini_style(theme_mode):
    if theme_mode == "Light":
        css = """
<style>
.stApp { background: #f1f3f4; color: #111827; }
section[data-testid="stSidebar"] { background: #eef1f4; border-right: 0px solid transparent; }
section[data-testid="stSidebar"] * { color: #111827 !important; }
.arapai-hero { padding: 0.2rem 0 0.6rem 0.1rem; }
.arapai-title { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-bottom: .25rem; color: #111827; }
.arapai-sub { color: #5f6368; font-size: 1rem; }
.stSelectbox label, .stCheckbox label, .stCaption { color: #374151 !important; }
.st-emotion-cache-1y4p8pa { max-width: 900px; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  color: #111827 !important;
  border-radius: 14px !important;
}
[data-testid="stChatInput"] > div {
  border-radius: 28px !important;
  border: 1px solid #e5e7eb !important;
  background: #ffffff !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
}
[data-testid="stChatInput"] input {
  color: #111827 !important;
}
[data-testid="stChatMessage"] { background: transparent !important; border: 0 !important; }
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li {
  color: #111827 !important;
}
[data-testid="stChatMessageAvatar"] { display: none !important; }
[data-testid="stCheckbox"] label span {
  color: #111827 !important;
}

/* Reduce Streamlit chrome for a cleaner Gemini-like canvas */
header, footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; height: 0px; }
</style>
"""
    else:
        css = """
<style>
.stApp { background: #0b1020; color: #e5e7eb; }
section[data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1f2937; }
section[data-testid="stSidebar"] * { color: #e5e7eb !important; }
.arapai-hero { padding: 0.2rem 0 0.6rem 0.1rem; }
.arapai-title { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-bottom: .25rem; }
.arapai-sub { color: #9ca3af; font-size: 1rem; }
.stChatInput > div { border-radius: 24px !important; border: 1px solid #374151 !important; background: #111827 !important; }
.stSelectbox label, .stCheckbox label { color: #d1d5db !important; }
.st-emotion-cache-1y4p8pa { max-width: 900px; }
[data-testid="stChatMessage"] {
  background: #151b2d !important;
  border: 1px solid #2a3247 !important;
  border-radius: 12px !important;
  padding: 0.35rem 0.6rem !important;
}
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li {
  color: #e5e7eb !important;
}
/* Hide Streamlit chat avatars (red/yellow icons) */
[data-testid="stChatMessageAvatar"] { display: none !important; }
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def _model_error_message(exc):
    err = f"{type(exc).__name__}: {exc!s}" if str(exc).strip() else f"{type(exc).__name__}"
    return f"Sorry, the model could not respond: {err}"


def _word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def _sentence_count(text):
    return len([p for p in re.split(r"[.!?]+", text or "") if p.strip()])


def _numbered_steps_count(text):
    return len(re.findall(r"(?m)^\s*\d+[.)]\s+\S+", text or ""))


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


def _is_meta_response(text):
    lower_text = (text or "").lower()
    if not lower_text.strip():
        return True
    return any(phrase in lower_text for phrase in BANNED_PHRASES)


def _is_level_compliant(level, text):
    words = _word_count(text)
    steps = _numbered_steps_count(text)
    if _is_meta_response(text):
        return False

    # Keep checks permissive enough to avoid over-correction.
    if words < 8:
        return False
    sents = _sentence_count(text)
    # Keep these permissive so we don't reject good answers.
    if level == "basic":
        return 1 <= sents <= 2 and words <= 60 and steps == 0
    if level == "lower_secondary":
        return 1 <= sents <= 5 and 15 <= words <= 220 and steps == 0
    if level == "upper_secondary":
        return 30 <= words <= 380
    if level == "technical":
        return words >= 60
    return True


def _regenerate_for_level(prompt, level, model_tier):
    compliance_hint = (
        "\n\nIMPORTANT RETRY RULE:\n"
        f"Your previous answer did not satisfy level='{level}'. "
        "Regenerate and strictly follow all response rules, including format and length. "
        "Do not apologize and do not reference previous answers. "
        "Answer only the user's latest question directly."
    )
    return generate(prompt + compliance_hint, model_tier=model_tier)


def _ensure_valid_reply(prompt, level, model_tier, reply):
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
    debug["initial_words"] = _word_count(reply)
    debug["initial_sentences"] = _sentence_count(reply)
    debug["initial_steps"] = _numbered_steps_count(reply)
    debug["initial_compliant"] = bool(reply and _is_level_compliant(level, reply))
    if debug["initial_compliant"]:
        debug["final_compliant"] = True
        debug["result_source"] = "initial"
        return reply, debug

    debug["retry_used"] = True
    retry = _regenerate_for_level(prompt, level, model_tier).strip()
    debug["retry_words"] = _word_count(retry)
    debug["retry_sentences"] = _sentence_count(retry)
    debug["retry_steps"] = _numbered_steps_count(retry)
    debug["retry_compliant"] = bool(retry and _is_level_compliant(level, retry))
    if debug["retry_compliant"]:
        debug["final_compliant"] = True
        debug["result_source"] = "retry"
        return retry, debug

    # If we have a non-compliant answer but it's not meta/system/apology text, return it.
    if retry and not _is_meta_response(retry):
        debug["final_compliant"] = False
        debug["result_source"] = "retry_noncompliant"
        return retry, debug
    if reply and not _is_meta_response(reply):
        debug["final_compliant"] = False
        debug["result_source"] = "initial_noncompliant"
        return reply, debug

    # Otherwise, do a stricter final retry to avoid meta/apology replies.
    final = generate(
        prompt
        + "\n\nFINAL RETRY RULE:\n"
        + "Answer the latest user question directly at the selected level. "
        + "No apology, no meta commentary. Do not describe yourself or the system; explain the topic only.",
        model_tier=model_tier,
    ).strip()
    if final:
        debug["final_compliant"] = _is_level_compliant(level, final)
        debug["result_source"] = "final_retry"
        return final, debug
    debug["final_compliant"] = False
    debug["result_source"] = "hard_fallback"
    return "I could not generate a valid explanation. Please ask again.", debug


def _request_regen():
    if not st.session_state.edit_mode:
        st.session_state.pending_regen = True


# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "level" not in st.session_state or st.session_state.level not in LEVELS:
    st.session_state.level = "lower_secondary"
MODEL_TIERS = ["Light", "Standard", "Advanced"]
if "model_tier" not in st.session_state or st.session_state.model_tier not in MODEL_TIERS:
    st.session_state.model_tier = "Light"
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "pending_regen" not in st.session_state:
    st.session_state.pending_regen = False
if "use_rag" not in st.session_state:
    st.session_state.use_rag = False
if "debug_level_checks" not in st.session_state:
    st.session_state.debug_level_checks = False
if "last_debug_info" not in st.session_state:
    st.session_state.last_debug_info = None
if "theme_mode" not in st.session_state or st.session_state.theme_mode not in ("Dark", "Light"):
    st.session_state.theme_mode = "Dark"

_inject_gemini_style(st.session_state.theme_mode)

if "warmed" not in st.session_state:
    try:
        warm_up(st.session_state.model_tier.lower())
        st.session_state.warmed = True
    except Exception as e:
        st.error(_model_error_message(e))
        st.info(
            "Make sure you have a valid GGUF file at one of:\n"
            "- `models/lite/model.gguf`\n"
            "- `models/standard/model.gguf`\n"
            "- `models/advanced/model.gguf`\n\n"
            "Then restart the app."
        )
        st.stop()

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### Arapai")
    st.button("New chat", use_container_width=True, on_click=lambda: st.session_state.update(messages=[], edit_mode=False))
    st.markdown("---")
    st.caption("Offline AI Tutor")
    st.selectbox("Theme", options=["Dark", "Light"], key="theme_mode")
    st.markdown("---")
    st.selectbox(
        "Model",
        options=MODEL_TIERS,
        key="model_tier",
        help="Select model tier manually. Light is default for fastest and most stable startup.",
    )
    st.checkbox("Use reference documents (PDFs)", key="use_rag")
    st.markdown("---")
    st.checkbox("Debug level compliance", key="debug_level_checks")

# ---------- TOP/HERO ----------
st.markdown(
    """
<div class="arapai-hero">
  <div class="arapai-title">Arapai</div>
  <div class="arapai-sub">Offline tutor with adjustable explanation depth and local model control.</div>
</div>
""",
    unsafe_allow_html=True,
)

ctrl1, = st.columns([1])
with ctrl1:
    st.selectbox(
        "Explanation level",
        options=list(LEVEL_ORDER),
        key="level",
        format_func=lambda k: LEVEL_LABELS[k],
        on_change=_request_regen,
    )
    st.caption(f"Selected behavior: {LEVEL_HINTS.get(st.session_state.level, '')}")

# ---------- REGENERATE ON LEVEL CHANGE ----------
if st.session_state.pending_regen and not st.session_state.edit_mode:
    st.session_state.pending_regen = False
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    last_user = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), None)
    if last_user:
        math_result = solve(last_user)
        retrieved_text = None
        if st.session_state.use_rag:
            try:
                retrieved_text = retrieve(last_user)
            except FileNotFoundError:
                st.warning(
                    "Reference documents not indexed. Put PDFs in **data/raw_pdfs** or **data/rawpdfs**, "
                    "then run: `python -m ingestion.ingest_pdf`"
                )
        prompt = build_prompt(st.session_state.level, st.session_state.messages[-6:], retrieved_text)
        tier = st.session_state.model_tier.lower()
        with st.spinner("Regenerating..."):
            if math_result is not None:
                reply = f"The result is {math_result}."
                st.session_state.last_debug_info = {
                    "selected_level": st.session_state.level,
                    "initial_compliant": True,
                    "retry_used": False,
                    "retry_compliant": False,
                    "final_compliant": True,
                    "result_source": "math",
                }
            else:
                try:
                    reply, debug = _ensure_valid_reply(
                        prompt,
                        st.session_state.level,
                        tier,
                        generate(prompt, model_tier=tier),
                    )
                    st.session_state.last_debug_info = debug
                except Exception as e:
                    reply = _model_error_message(e)
                    st.session_state.last_debug_info = {"error": str(e)}
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

# ---------- DISPLAY CHAT ----------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "user" and i == len(st.session_state.messages) - 2 and not st.session_state.edit_mode:
            if st.button("Edit last question", key=f"edit-{i}"):
                st.session_state.edit_mode = True

# ---------- EDIT MODE ----------
if st.session_state.edit_mode and len(st.session_state.messages) >= 2:
    last_user = st.session_state.messages[-2]["content"]
    edited = st.text_area("Edit your last question", last_user)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save & Regenerate"):
            st.session_state.messages[-2]["content"] = edited
            st.session_state.edit_mode = False
            st.session_state.pending_regen = True
            st.rerun()
    with c2:
        if st.button("Cancel"):
            st.session_state.edit_mode = False
            st.rerun()

# ---------- INPUT ----------
if not st.session_state.edit_mode:
    user_input = st.chat_input("Ask Arapai")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        math_result = solve(user_input)
        retrieved_text = None
        if st.session_state.use_rag:
            try:
                retrieved_text = retrieve(user_input)
            except FileNotFoundError:
                st.warning(
                    "Reference documents not indexed. Put PDFs in **data/raw_pdfs** or **data/rawpdfs**, "
                    "then run: `python -m ingestion.ingest_pdf`"
                )

        prompt = build_prompt(st.session_state.level, st.session_state.messages[-6:], retrieved_text)
        with st.chat_message("assistant"):
            tier = st.session_state.model_tier.lower()
            if math_result is not None:
                reply = f"The result is {math_result}."
                st.session_state.last_debug_info = {
                    "selected_level": st.session_state.level,
                    "initial_compliant": True,
                    "retry_used": False,
                    "retry_compliant": False,
                    "final_compliant": True,
                    "result_source": "math",
                }
                st.markdown(reply)
            else:
                try:
                    ph = st.empty()
                    reply = ""
                    for chunk in generate_stream(prompt, model_tier=tier):
                        reply += chunk
                        ph.markdown(reply + "▌")
                    if not reply.strip():
                        # If streaming returns nothing, fallback to non-stream generation.
                        reply = generate(prompt, model_tier=tier)
                    reply, debug = _ensure_valid_reply(prompt, st.session_state.level, tier, reply)
                    st.session_state.last_debug_info = debug
                    ph.markdown(reply)
                except Exception as e:
                    reply = _model_error_message(e)
                    st.session_state.last_debug_info = {"error": str(e)}
                    st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

if st.session_state.debug_level_checks and st.session_state.last_debug_info:
    st.markdown("### Debug: Level Compliance")
    st.json(st.session_state.last_debug_info)