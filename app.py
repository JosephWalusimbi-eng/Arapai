import streamlit as st
import re
from backend.llm_engine import warm_up, generate, generate_stream
from backend.prompt_builder import build_prompt, LEVELS, LEVEL_ORDER, LEVEL_LABELS, LEVEL_HINTS
from backend.rag_engine import retrieve
from backend.math_engine import solve

st.set_page_config(page_title="Arapai", layout="centered")


def _model_error_message(exc):
    """Turn low-level model errors into a user-friendly message."""
    err = f"{type(exc).__name__}: {exc!s}" if str(exc).strip() else f"{type(exc).__name__}"
    if isinstance(exc, AssertionError):
        return (
            f"Sorry, the model could not respond ({err}). "
            "This can happen with the Advanced model on some systems. "
            "**Try selecting “Standard” or “Light” in the Model menu** and ask again."
        )
    return f"Sorry, the model could not respond: {err}"


def _word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def _sentence_count(text):
    parts = re.split(r"[.!?]+", text or "")
    return len([p for p in parts if p.strip()])


def _numbered_steps_count(text):
    return len(re.findall(r"(?m)^\s*\d+[.)]\s+\S+", text or ""))


def _is_level_compliant(level, text):
    words = _word_count(text)
    sentences = _sentence_count(text)
    steps = _numbered_steps_count(text)
    lower_text = (text or "").lower()
    banned_phrases = (
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
    )
    if any(phrase in lower_text for phrase in banned_phrases):
        return False

    if level == "basic":
        return 1 <= sentences <= 2 and words <= 45 and steps == 0
    if level == "basic_detailed":
        return 2 <= sentences <= 3 and 40 <= words <= 95 and "for example" in lower_text and steps == 0
    if level == "standard":
        return 2 <= sentences <= 3 and 45 <= words <= 95 and steps == 0
    if level == "standard_detailed":
        return 130 <= words <= 220 and 3 <= steps <= 4
    if level == "advanced":
        return 3 <= sentences <= 4 and 70 <= words <= 140 and steps == 0
    if level == "advanced_detailed":
        return 220 <= words <= 360 and 5 <= steps <= 8
    return True


def _regenerate_for_level(prompt, level, model_tier):
    """
    One-shot regeneration pass when the first answer doesn't follow level rules.
    """
    compliance_hint = (
        "\n\nIMPORTANT RETRY RULE:\n"
        f"Your previous answer did not satisfy level='{level}'. "
        "Regenerate and strictly follow all response rules, including format and length. "
        "Do not apologize and do not reference previous answers. "
        "Answer only the user's latest question directly."
    )
    return generate(prompt + compliance_hint, model_tier=model_tier)


def _ensure_valid_reply(prompt, level, model_tier, reply):
    """
    Ensure we never return empty or meta filler text.
    One retry for compliance, one stricter retry if still invalid.
    """
    reply = (reply or "").strip()
    if reply and _is_level_compliant(level, reply):
        return reply

    retry = _regenerate_for_level(prompt, level, model_tier).strip()
    if retry and _is_level_compliant(level, retry):
        return retry

    final_hint = (
        "\n\nFINAL RETRY RULE:\n"
        "Return only the final explanation content.\n"
        "No preface, no apology, no meta commentary.\n"
        "Do not say you are about to explain; just explain now."
    )
    final = generate(prompt + final_hint, model_tier=model_tier).strip()
    if final:
        return final
    return "I could not generate a valid explanation. Please ask again."

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "level" not in st.session_state or st.session_state.level not in LEVELS:
    st.session_state.level = "standard"

MODEL_TIERS = ["Light", "Standard", "Advanced"]
if "model_tier" not in st.session_state or st.session_state.model_tier not in MODEL_TIERS:
    st.session_state.model_tier = "Light"

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "pending_regen" not in st.session_state:
    st.session_state.pending_regen = False

if "warmed" not in st.session_state:
    _tier = st.session_state.model_tier.lower()
    try:
        warm_up(_tier)
        st.session_state.warmed = True
    except Exception as e:
        st.session_state.warmed = False
        st.error(_model_error_message(e))
        st.info(
            "Make sure you have a valid GGUF file at one of:\n"
            "- `models/lite/model.gguf`\n"
            "- `models/standard/model.gguf`\n"
            "- `models/advanced/model.gguf`\n\n"
            "Then restart the app."
        )
        st.stop()

# ---------- UI ----------
st.title("Arapai – Offline AI Education ChatBot")

def _request_regen():
    if not st.session_state.edit_mode:
        st.session_state.pending_regen = True

st.selectbox(
    "Explanation level:",
    options=list(LEVEL_ORDER),
    key="level",
    format_func=lambda k: LEVEL_LABELS[k],
    on_change=_request_regen,
)
st.caption(f"Selected behavior: {LEVEL_HINTS.get(st.session_state.level, '')}")

st.selectbox(
    "Model:",
    options=MODEL_TIERS,
    key="model_tier",
    help="Select model tier manually. Light is the default for fastest and most stable startup.",
)

use_rag = st.checkbox("Use reference documents (PDFs)", value=False)

# ---------- REGENERATE ON LEVEL CHANGE ----------
if st.session_state.pending_regen and not st.session_state.edit_mode:
    st.session_state.pending_regen = False
    if len(st.session_state.messages) >= 2 and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
        last_user = next(
            (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
            None,
        )
        if last_user:
            math_result = solve(last_user)
            retrieved_text = None
            if use_rag:
                try:
                    retrieved_text = retrieve(last_user)
                except FileNotFoundError:
                    st.warning(
                        "Reference documents not indexed. Put PDFs in **data/raw_pdfs** or **data/rawpdfs**, "
                        "then run: `python -m ingestion.ingest_pdf`"
                    )
            history = st.session_state.messages[-6:]
            prompt = build_prompt(st.session_state.level, history, retrieved_text)
            _tier = st.session_state.model_tier.lower()
            with st.spinner("Regenerating..."):
                if math_result is not None:
                    reply = f"The result is {math_result}."
                else:
                    try:
                        reply = generate(prompt, model_tier=_tier)
                        reply = _ensure_valid_reply(
                            prompt,
                            st.session_state.level,
                            _tier,
                            reply,
                        )
                    except Exception as e:
                        reply = _model_error_message(e)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

# ---------- DISPLAY CHAT ----------
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if (
            msg["role"] == "user"
            and i == len(st.session_state.messages) - 2
            and not st.session_state.edit_mode
        ):
            if st.button("Edit last question"):
                st.session_state.edit_mode = True

# ---------- EDIT MODE ----------
if st.session_state.edit_mode:
    last_user = st.session_state.messages[-2]["content"]
    edited = st.text_area("Edit your last question:", last_user)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save & Regenerate"):
            st.session_state.messages[-2]["content"] = edited
            st.session_state.edit_mode = False
            st.session_state.pending_regen = True
            st.rerun()

    with col2:
        if st.button("Cancel"):
            st.session_state.edit_mode = False
            st.rerun()

# ---------- INPUT ----------
if not st.session_state.edit_mode:
    user_input = st.chat_input("Ask a question")

    if user_input:
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # Try math first
        math_result = solve(user_input)

        retrieved_text = None
        if use_rag:
            try:
                retrieved_text = retrieve(user_input)
            except FileNotFoundError:
                st.warning(
                    "Reference documents not indexed. Put PDFs in **data/raw_pdfs** or **data/rawpdfs**, "
                    "then run: `python -m ingestion.ingest_pdf`"
                )

        HISTORY_LIMIT = 6
        history = st.session_state.messages[-HISTORY_LIMIT:]

        prompt = build_prompt(
            st.session_state.level,
            history,
            retrieved_text
        )

        with st.chat_message("assistant"):
            _tier = st.session_state.model_tier.lower()
            if math_result is not None:
                reply = f"The result is {math_result}."
                st.markdown(reply)
            else:
                try:
                    stream_placeholder = st.empty()
                    reply = ""
                    for chunk in generate_stream(prompt, model_tier=_tier):
                        reply += chunk
                        stream_placeholder.markdown(reply + "▌")
                    reply = _ensure_valid_reply(
                        prompt,
                        st.session_state.level,
                        _tier,
                        reply,
                    )
                    stream_placeholder.markdown(reply)
                except Exception as e:
                    reply = _model_error_message(e)
                    st.markdown(reply)

        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })

# ---------- RESET ----------
if st.button("New Chat"):
    st.session_state.messages = []
    st.session_state.edit_mode = False

    # IMPORTANT: do NOT touch model or warm_up
    st.rerun()