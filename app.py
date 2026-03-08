import streamlit as st
from backend.llm_engine import warm_up, generate, generate_stream
from backend.prompt_builder import build_prompt, LEVELS
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

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "level" not in st.session_state or st.session_state.level not in LEVELS:
    st.session_state.level = list(LEVELS.keys())[0]

if "model_tier" not in st.session_state:
    st.session_state.model_tier = "Auto"

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

if "pending_regen" not in st.session_state:
    st.session_state.pending_regen = False

if "warmed" not in st.session_state:
    _tier = None if st.session_state.model_tier == "Auto" else st.session_state.model_tier.lower()
    warm_up(_tier)
    st.session_state.warmed = True

# ---------- UI ----------
st.title("Arapai – Offline AI Education ChatBot")

def _request_regen():
    if not st.session_state.edit_mode:
        st.session_state.pending_regen = True

st.selectbox(
    "Explanation level:",
    options=list(LEVELS.keys()),
    index=list(LEVELS.keys()).index(st.session_state.level),
    key="level",
    on_change=_request_regen,
)

MODEL_TIERS = ["Auto", "Light", "Standard", "Advanced"]
st.selectbox(
    "Model:",
    options=MODEL_TIERS,
    index=MODEL_TIERS.index(st.session_state.model_tier) if st.session_state.model_tier in MODEL_TIERS else 0,
    key="model_tier",
    help="Auto picks by RAM. Override to force Light, Standard, or Advanced (may require more RAM).",
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
            _tier = None if st.session_state.model_tier == "Auto" else st.session_state.model_tier.lower()
            with st.spinner("Regenerating..."):
                if math_result is not None:
                    reply = f"The result is {math_result}."
                else:
                    try:
                        reply = generate(prompt, model_tier=_tier)
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
            st.session_state.messages.pop()
            st.session_state.edit_mode = False
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
            _tier = None if st.session_state.model_tier == "Auto" else st.session_state.model_tier.lower()
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