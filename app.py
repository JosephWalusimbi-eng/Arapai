import streamlit as st
from backend.cbc_engine import (
    build_curated_mistake_explanation,
    build_mistake_prompt_for_level,
    check_answer as cbc_check_answer,
)
from backend.llm_engine import generate
from backend.memory_utils import log_memory_usage, memory_summary, peak_rss_mb
from backend.online_gemma import generate as online_generate
from backend.demo_replies import SAMPLE_PROMPTS, get_curated_demo_reply
from backend.math_engine import solve, solve_in_text, build_mixed_math_reply
from backend.prompt_builder import (
    LEVEL_HINTS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    LEVELS,
    build_prompt,
)
from backend.rag_engine import retrieve, unload_resources as unload_rag
from backend.tutor_engine import ensure_valid_reply

st.set_page_config(page_title="Arapai- Offline AI Tutor", layout="wide")


import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "cbc_content.json")

with open(DATA_PATH, "r") as f:
    cbc_content = json.load(f)


def _inject_gemini_style(theme_mode):
    if theme_mode == "Light":
        css = """
<style>
:root {
  --arapai-bg: #fdfaf6;
  --arapai-surface: #ffffff;
  --arapai-sidebar: #f5f0ea;
  --arapai-text: #1a1614;
  --arapai-muted: #5c534a;
  --arapai-border: #e8dfd4;
  --arapai-accent: #26a688;
  --arapai-accent-hover: #1f8a72;
}

.stApp,
[data-testid="stAppViewContainer"] {
  background: var(--arapai-bg) !important;
  color: var(--arapai-text) !important;
}

section[data-testid="stSidebar"] {
  background: var(--arapai-sidebar) !important;
  border-right: 1px solid var(--arapai-border) !important;
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
section[data-testid="stSidebar"] [data-testid="stHeading"],
section[data-testid="stSidebar"] [data-testid="stHeading"] * {
  color: var(--arapai-text) !important;
}

.arapai-sidebar-title {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.25;
  margin: 0 0 0.35rem 0;
  color: var(--arapai-text) !important;
}

.arapai-sidebar-caption {
  color: var(--arapai-muted) !important;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
}

section[data-testid="stSidebar"] hr,
section[data-testid="stSidebar"] [data-testid="stDivider"] {
  border-color: var(--arapai-border) !important;
  opacity: 1 !important;
}

section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="select"] span,
section[data-testid="stSidebar"] [data-baseweb="select"] input {
  color: var(--arapai-text) !important;
  background: var(--arapai-surface) !important;
}

.arapai-hero { padding: 0.2rem 0 0.6rem 0.1rem; }
.arapai-title {
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: .25rem;
  color: var(--arapai-text) !important;
}
.arapai-sub { color: var(--arapai-muted) !important; font-size: 1rem; }

.stSelectbox label,
.stCheckbox label,
.stCaption,
[data-testid="stWidgetLabel"],
p, li, span, label {
  color: var(--arapai-text);
}

.st-emotion-cache-1y4p8pa { max-width: 900px; }

[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: var(--arapai-surface) !important;
  border: 1px solid var(--arapai-border) !important;
  color: var(--arapai-text) !important;
  border-radius: 12px !important;
}

/* Buttons — light surfaces, readable text */
.stButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="baseButton-secondary"] {
  background: var(--arapai-surface) !important;
  color: var(--arapai-text) !important;
  border: 1px solid var(--arapai-border) !important;
  border-radius: 10px !important;
  box-shadow: 0 1px 2px rgba(26, 22, 20, 0.06) !important;
}

.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="baseButton-secondary"]:hover {
  background: #fff8f0 !important;
  border-color: var(--arapai-accent) !important;
  color: var(--arapai-text) !important;
}

.stButton > button p,
.stButton > button span,
.stButton > button div,
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-secondary"] span,
[data-testid="baseButton-secondary"] p,
[data-testid="baseButton-secondary"] span {
  color: var(--arapai-text) !important;
}

.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"],
[data-testid="baseButton-primary"] {
  background: var(--arapai-accent) !important;
  color: #ffffff !important;
  border: 1px solid var(--arapai-accent) !important;
}

.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span {
  color: #ffffff !important;
}

section[data-testid="stSidebar"] .stButton > button {
  background: var(--arapai-surface) !important;
  color: var(--arapai-text) !important;
}

/* Chat area — no black footer bar */
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
[data-testid="stChatInputContainer"] {
  background: var(--arapai-bg) !important;
}

[data-testid="stChatInput"] > div {
  border-radius: 24px !important;
  border: 1px solid var(--arapai-border) !important;
  background: var(--arapai-surface) !important;
  box-shadow: 0 2px 8px rgba(26, 22, 20, 0.06) !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {
  color: var(--arapai-text) !important;
  background: transparent !important;
}

[data-testid="stChatInput"] textarea::placeholder {
  color: var(--arapai-muted) !important;
}

[data-testid="stChatMessage"] {
  background: var(--arapai-surface) !important;
  border: 1px solid var(--arapai-border) !important;
  border-radius: 12px !important;
}

[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] *,
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li,
[data-testid="stChatMessageContent"] span,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span {
  color: var(--arapai-text) !important;
}

[data-testid="stChatMessageAvatar"] { display: none !important; }

[data-testid="stCheckbox"] label span {
  color: var(--arapai-text) !important;
}

/* Alerts */
[data-testid="stAlert"] {
  border-radius: 10px !important;
}

header, footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; height: 0px; }
</style>
"""
    else:
        css = """
<style>
.stApp { background: #0e1117; color: #fafafa; }
section[data-testid="stSidebar"] { background: #262730; border-right: 1px solid #3e3e3e; }
section[data-testid="stSidebar"] * { color: #fafafa !important; }
.arapai-hero { padding: 0.2rem 0 0.6rem 0.1rem; }
.arapai-title { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-bottom: .25rem; color: #ffffff; }
.arapai-sub { color: #b2b7c4; font-size: 1rem; }
.stChatInput > div { border-radius: 24px !important; border: 1px solid #4f555b !important; background: #262730 !important; }
.stSelectbox label, .stCheckbox label { color: #fafafa !important; }
.st-emotion-cache-1y4p8pa { max-width: 900px; }
[data-testid="stChatMessage"] {
  background: #262730 !important;
  border: 1px solid #3e3e3e !important;
  border-radius: 12px !important;
  padding: 0.35rem 0.6rem !important;
}
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li {
  color: #fafafa !important;
}
/* Hide Streamlit chat avatars (red/yellow icons) */
[data-testid="stChatMessageAvatar"] { display: none !important; }
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def _coerce_reply(reply):
    text = (reply or "").strip()
    if text:
        return text
    return (
        "I could not generate a response. "
        "Activate the project venv, ensure the model is downloaded, then try again."
    )


def _check_offline_runtime():
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return (
            "Missing `llama_cpp`. Activate the venv first:\n"
            "`.\venv\\Scripts\\Activate.ps1` then `streamlit run app.py`"
        )
    try:
        from backend.llm_engine import get_model_path

        get_model_path("light")
    except RuntimeError as exc:
        return str(exc)
    return None


def _model_error_message(exc):
    err = f"{type(exc).__name__}: {exc!s}" if str(exc).strip() else f"{type(exc).__name__}"
    if "HF token missing" in err:
        return (
            "Online mode needs a Hugging Face token.\n\n"
            "- Set environment variable `HF_TOKEN` (or `HUGGINGFACEHUB_API_TOKEN`).\n"
            "- Restart the app.\n\n"
            f"Details: {err}"
        )
    return f"Sorry, the model could not respond: {err}"


def _offline_generate(prompt, model_tier=None, max_tokens=256):
    return generate(prompt, max_tokens=max_tokens, model_tier=model_tier)


def _tutor_generate(prompt, model_tier=None, max_tokens=256):
    if st.session_state.run_mode == "Online (Gemma 1.1)":
        return online_generate(prompt, max_tokens=max_tokens)
    return _offline_generate(prompt, model_tier=model_tier, max_tokens=max_tokens)


def _ensure_valid_reply(prompt, level, model_tier, reply):
    return ensure_valid_reply(prompt, level, model_tier, reply, _tutor_generate)


def _build_assistant_reply(user_text, conversation_history=None):
    runtime_error = _check_offline_runtime()
    if runtime_error and st.session_state.run_mode == "Offline":
        st.session_state.last_debug_info = {"error": runtime_error}
        return runtime_error, None

    history = (
        conversation_history
        if conversation_history is not None
        else st.session_state.messages[-6:]
    )
    math_result = solve_in_text(user_text)
    retrieved_text, rag_warning = _retrieve_if_enabled(user_text)
    if st.session_state.use_rag:
        unload_rag()
    wants_explanation = bool(re.search(r"\b(then|explain|why|how)\b", user_text, re.I))
    tier = st.session_state.model_tier.lower()
    log_memory_usage("before_inference")

    if math_result is not None and wants_explanation:
        reply = build_mixed_math_reply(st.session_state.level, user_text, math_result)
        st.session_state.last_debug_info = {
            "selected_level": st.session_state.level,
            "initial_compliant": True,
            "retry_used": False,
            "retry_compliant": False,
            "final_compliant": True,
            "result_source": "math_explain",
        }
        return reply, rag_warning

    curated = get_curated_demo_reply(user_text, st.session_state.level)
    if curated:
        st.session_state.last_debug_info = {
            "selected_level": st.session_state.level,
            "initial_compliant": True,
            "retry_used": False,
            "retry_compliant": False,
            "final_compliant": True,
            "result_source": "demo_curated",
        }
        return curated, rag_warning

    prompt = build_prompt(st.session_state.level, history, retrieved_text)

    if math_result is not None and not wants_explanation:
        reply = f"The result is {math_result}."
        st.session_state.last_debug_info = {
            "selected_level": st.session_state.level,
            "initial_compliant": True,
            "retry_used": False,
            "retry_compliant": False,
            "final_compliant": True,
            "result_source": "math",
        }
        return reply, rag_warning

    try:
        if st.session_state.run_mode == "Online (Gemma 1.1)":
            raw = online_generate(prompt)
        else:
            raw = generate(prompt, model_tier=tier)
            if not (raw or "").strip():
                raw = generate(prompt, model_tier=tier)
        reply, debug = _ensure_valid_reply(prompt, st.session_state.level, tier, raw)
        st.session_state.last_debug_info = debug
        return reply, rag_warning
    except Exception as exc:
        st.session_state.last_debug_info = {"error": str(exc)}
        return _model_error_message(exc), rag_warning


def _pending_assistant_user_text():
    if st.session_state.edit_mode or st.session_state.mode != "chat":
        return None
    msgs = st.session_state.messages
    if msgs and msgs[-1]["role"] == "user":
        return msgs[-1]["content"]
    return None


def _regenerate_all_assistant_replies():
    spinner_msg = (
        "Regenerating all replies at the selected explanation level… "
        "This may take a few minutes offline."
        if st.session_state.run_mode == "Offline"
        else "Regenerating all replies at the selected explanation level…"
    )
    with st.spinner(spinner_msg):
        rebuilt = []
        pending_rag_warning = None
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                rebuilt.append(msg)
                continue
            if msg["role"] != "assistant":
                rebuilt.append(msg)
                continue
            user_text = rebuilt[-1]["content"] if rebuilt and rebuilt[-1]["role"] == "user" else None
            if not user_text:
                rebuilt.append(msg)
                continue
            history = rebuilt[-6:]
            reply, rag_warning = _build_assistant_reply(user_text, conversation_history=history)
            if rag_warning:
                pending_rag_warning = rag_warning
            rebuilt.append({"role": "assistant", "content": _coerce_reply(reply)})
        st.session_state.messages = rebuilt
        if pending_rag_warning:
            st.session_state._pending_rag_warning = pending_rag_warning


def _complete_assistant_reply(user_text):
    spinner_msg = (
        "Loading local model and generating answer… "
        "The first reply can take 1–2 minutes."
        if st.session_state.run_mode == "Offline"
        else "Thinking…"
    )
    with st.spinner(spinner_msg):
        reply, rag_warning = _build_assistant_reply(user_text)
    if rag_warning:
        st.session_state._pending_rag_warning = rag_warning
    st.session_state.messages.append({"role": "assistant", "content": _coerce_reply(reply)})


def _retrieve_if_enabled(query):
    if not st.session_state.use_rag:
        return None, None
    try:
        chunks = retrieve(query)
        if not (chunks or "").strip():
            return None, (
                "RAG is on, but no relevant excerpts matched this question in the indexed PDFs."
            )
        return chunks, None
    except FileNotFoundError:
        return None, (
            "Reference documents not indexed. Put PDFs in **data/raw_pdfs**, "
            "then run: `python -m ingestion.ingest_pdf`"
        )
    except Exception as exc:
        return None, f"RAG could not load: {exc}"


def _request_regen():
    if not st.session_state.edit_mode:
        st.session_state.pending_regen = True


def _sync_explanation_level_change():
    prev = st.session_state.get("_prev_explanation_level")
    current = st.session_state.level
    if prev is None:
        st.session_state._prev_explanation_level = current
        return
    if prev == current or st.session_state.edit_mode or st.session_state.mode != "chat":
        st.session_state._prev_explanation_level = current
        return
    st.session_state._prev_explanation_level = current
    if any(m.get("role") == "assistant" for m in st.session_state.messages):
        st.session_state.pending_regen_all = True


def _clear_cbc_feedback_state():
    st.session_state.cbc_pending_feedback = None
    st.session_state.cbc_mistake_explanation = None


def _generate_cbc_mistake_explanation(question, user_answer, topic, correct_answers):
    tier = st.session_state.model_tier.lower()
    log_memory_usage("cbc_explain_start")

    if st.session_state.run_mode == "Offline":
        reply = build_curated_mistake_explanation(
            st.session_state.level,
            question,
            user_answer,
            topic,
            correct_answers,
        )
        debug = {
            "selected_level": st.session_state.level,
            "initial_compliant": True,
            "retry_used": False,
            "retry_compliant": False,
            "final_compliant": True,
            "result_source": "cbc_curated",
            "memory": memory_summary(),
        }
        return reply, debug

    rag_query = f"{topic}. {question}"
    retrieved_text, rag_warning = _retrieve_if_enabled(rag_query)
    if st.session_state.use_rag:
        unload_rag()
    prompt = build_mistake_prompt_for_level(
        st.session_state.level,
        question,
        user_answer,
        topic,
        correct_answers,
        retrieved_text,
    )

    try:
        raw = _tutor_generate(prompt, model_tier=tier)
        reply, debug = _ensure_valid_reply(prompt, st.session_state.level, tier, raw)
        if rag_warning:
            debug["rag_warning"] = rag_warning
        debug["memory"] = memory_summary()
        debug["result_source"] = debug.get("result_source", "llm")
        return reply, debug
    except Exception as e:
        reply = build_curated_mistake_explanation(
            st.session_state.level,
            question,
            user_answer,
            topic,
            correct_answers,
        )
        return reply, {"error": str(e), "result_source": "cbc_curated_fallback"}


def render_cbc_learn():
    st.title("CBC Learning Mode")

    if st.session_state.cbc_level is None:
        level = st.selectbox("Select Level", list(cbc_content.keys()))

        if st.button("Continue"):
            st.session_state.cbc_level = level
            st.rerun()

    elif st.session_state.cbc_topic is None:
        topics = [item["topic"] for item in cbc_content[st.session_state.cbc_level]]

        topic = st.selectbox("Select Topic", topics)

        if st.button("Load Questions"):
            st.session_state.cbc_topic = topic
            st.session_state.q_index = 0
            st.session_state.score = 0
            st.session_state.answers_log = []
            _clear_cbc_feedback_state()
            st.rerun()

    else:
        selected_items = [
            item for item in cbc_content[st.session_state.cbc_level]
            if item["topic"] == st.session_state.cbc_topic
        ]

        if "q_index" not in st.session_state:
            st.session_state.q_index = 0

        if "score" not in st.session_state:
            st.session_state.score = 0

        if "answers_log" not in st.session_state:
            st.session_state.answers_log = []

        questions = selected_items[0]["questions"]  # new structure

        if st.session_state.q_index >= len(questions):
            st.success("🎉 Topic Completed")

            total = len(questions)
            score = st.session_state.score

            st.write(f"### Score: {score} / {total}")

            st.markdown("## Corrections")

            for item in st.session_state.answers_log:
                st.write(f"**Question:** {item['question']}")
                st.write(f"Your Answer: {item['your_answer']}")
                st.write(f"Correct Answers: {', '.join(item['correct_answers'])}")
                st.write(f"Result: {item['result']}")
                st.markdown("---")

            if st.button("Restart Topic"):
                st.session_state.q_index = 0
                st.session_state.score = 0
                st.session_state.answers_log = []
                _clear_cbc_feedback_state()
                st.rerun()

            if st.button("Back to Topics"):
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

            if st.button("Back to Levels"):
                st.session_state.cbc_level = None
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

        elif st.session_state.cbc_pending_feedback:
            fb = st.session_state.cbc_pending_feedback
            topic = st.session_state.cbc_topic

            st.subheader(f"Question {st.session_state.q_index + 1}/{len(questions)}")
            st.write(fb["question"])

            if fb["result"] == "correct":
                st.success("Correct!")
            elif fb["result"] == "partial":
                st.warning("Partially correct — you captured some of the idea.")
            else:
                st.error("Not quite right.")

            st.write(f"**Your answer:** {fb['your_answer'] or '(blank)'}")

            if fb["result"] in ("wrong", "partial"):
                if st.session_state.cbc_mistake_explanation:
                    st.markdown("### Tutor explanation")
                    st.markdown(st.session_state.cbc_mistake_explanation)
                    st.caption(
                        f"Explanation level: {LEVEL_LABELS.get(st.session_state.level, st.session_state.level)}"
                    )
                    if st.session_state.last_debug_info and st.session_state.last_debug_info.get("rag_warning"):
                        st.warning(st.session_state.last_debug_info["rag_warning"])
                elif st.button("Explain my mistake", type="primary"):
                    with st.spinner("Preparing explanation..."):
                        explanation, debug = _generate_cbc_mistake_explanation(
                            fb["question"],
                            fb["your_answer"],
                            topic,
                            fb["correct_answers"],
                        )
                    st.session_state.cbc_mistake_explanation = explanation
                    st.session_state.last_debug_info = debug
                    st.rerun()

            if st.button("Next question"):
                _clear_cbc_feedback_state()
                st.session_state.q_index += 1
                st.rerun()

            st.markdown("---")

            if st.button("Back to Topics", key="cbc_back_topics_feedback"):
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

            if st.button("Back to Levels", key="cbc_back_levels_feedback"):
                st.session_state.cbc_level = None
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

        else:
            q = questions[st.session_state.q_index]

            st.subheader(f"Question {st.session_state.q_index + 1}/{len(questions)}")
            st.write(q["question"])

            user_answer = st.text_input("Your Answer")

            if st.button("Submit Answer"):
                tier = st.session_state.model_tier.lower()
                gen_fn = _offline_generate if st.session_state.run_mode == "Offline" else None
                result, keyword_score = cbc_check_answer(
                    user_answer,
                    q["answers"],
                    question=q["question"],
                    generate_fn=gen_fn,
                    model_tier=tier,
                )
                topic = st.session_state.cbc_topic

                # initialize topic score if not exists
                if topic not in st.session_state.scores:
                    st.session_state.scores[topic] = {
                        "score": 0,
                        "attempted": 0,
                        "total": len(questions)
                    }

                # update attempts
                st.session_state.scores[topic]["attempted"] += 1

                # scoring
                if result == "correct":
                    st.session_state.score += 1
                    st.session_state.scores[topic]["score"] += 1
                elif result == "partial":
                    st.session_state.score += 0.5
                    st.session_state.scores[topic]["score"] += 0.5

                # log answers
                st.session_state.answers_log.append({
                    "question": q["question"],
                    "your_answer": user_answer,
                    "correct_answers": q["answers"],
                    "result": result,
                    "keyword_score": keyword_score,
                })

                st.session_state.cbc_pending_feedback = {
                    "question": q["question"],
                    "your_answer": user_answer,
                    "correct_answers": q["answers"],
                    "result": result,
                }
                st.session_state.cbc_mistake_explanation = None
                st.rerun()

            st.markdown("---")

            if st.button("Back to Topics"):
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

            if st.button("Back to Levels"):
                st.session_state.cbc_level = None
                st.session_state.cbc_topic = None
                if "q_index" in st.session_state: del st.session_state["q_index"]
                if "score" in st.session_state: del st.session_state["score"]
                if "answers_log" in st.session_state: del st.session_state["answers_log"]
                _clear_cbc_feedback_state()
                st.rerun()

    st.markdown("---")
    st.markdown("## 📊 Your Progress")

    if st.session_state.scores:
        for topic, data in st.session_state.scores.items():
            score = data["score"]
            total = data["total"]
            attempted = data["attempted"]

            percent = (score / total) * 100 if total > 0 else 0
            progress_val = min(1.0, max(0.0, percent / 100))

            st.write(f"**{topic}**")
            st.write(f"Score: {score}/{total}")
            st.write(f"Attempted: {attempted}")
            st.progress(progress_val)
    else:
        st.info("No topics attempted yet.")


# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "level" not in st.session_state or st.session_state.level not in LEVEL_ORDER:
    st.session_state.level = "lower_secondary"
if "_prev_explanation_level" not in st.session_state:
    st.session_state._prev_explanation_level = st.session_state.level
MODEL_TIERS = ["Light", "Standard", "Advanced"]
if "model_tier" not in st.session_state or st.session_state.model_tier not in MODEL_TIERS:
    st.session_state.model_tier = "Light"
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "pending_regen" not in st.session_state:
    st.session_state.pending_regen = False
if "pending_regen_all" not in st.session_state:
    st.session_state.pending_regen_all = False
if "use_rag" not in st.session_state:
    st.session_state.use_rag = False
if "debug_level_checks" not in st.session_state:
    st.session_state.debug_level_checks = False
if "last_debug_info" not in st.session_state:
    st.session_state.last_debug_info = None
if "run_mode" not in st.session_state or st.session_state.run_mode not in ("Offline", "Online (Gemma 1.1)"):
    st.session_state.run_mode = "Offline"
if "theme_mode" not in st.session_state or st.session_state.theme_mode not in ("Dark", "Light"):
    st.session_state.theme_mode = "Dark"

if "mode" not in st.session_state:
    st.session_state.mode = "chat"

if "cbc_level" not in st.session_state:
    st.session_state.cbc_level = None

if "cbc_topic" not in st.session_state:
    st.session_state.cbc_topic = None
    
if "scores" not in st.session_state:
    st.session_state.scores = {}

if "cbc_pending_feedback" not in st.session_state:
    st.session_state.cbc_pending_feedback = None

if "cbc_mistake_explanation" not in st.session_state:
    st.session_state.cbc_mistake_explanation = None

_inject_gemini_style(st.session_state.theme_mode)
log_memory_usage("app_start")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown(
        '<div class="arapai-sidebar-title">Arapai- Offline AI Tutor</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.run_mode == "Offline":
        runtime_error = _check_offline_runtime()
        if runtime_error:
            st.error(runtime_error)
        else:
            st.caption("Local model ready (first reply may take 1–2 min to load).")
    if st.button("New Chat", use_container_width=True):
       st.session_state.mode = "chat"
       st.session_state.messages = []
       st.session_state.edit_mode = False

    if st.button("CBC-Learn", use_container_width=True):
       st.session_state.mode = "cbc"
    
    st.markdown("---")
    st.markdown(
        '<div class="arapai-sidebar-caption">Offline AI Tutor</div>',
        unsafe_allow_html=True,
    )
    st.selectbox("Theme", options=["Dark", "Light"], key="theme_mode")
    st.selectbox("Mode", options=["Offline", "Online (Gemma 1.1)"], key="run_mode")
    st.markdown("---")
    if st.session_state.run_mode == "Offline":
        st.selectbox(
            "Model",
            options=MODEL_TIERS,
            key="model_tier",
            help="Select model tier manually. Light is default for fastest and most stable startup.",
        )
    else:
        st.info("Online mode uses `google/gemma-1.1-7b-it`.")
    prev_rag = st.session_state.get("_prev_use_rag", st.session_state.use_rag)
    st.checkbox("Use reference documents (RAG)", key="use_rag", help="Loads PDF index only when enabled.")
    if prev_rag and not st.session_state.use_rag:
        unload_rag()
    st.session_state._prev_use_rag = st.session_state.use_rag
    st.markdown("---")
    st.checkbox("Debug level compliance", key="debug_level_checks")
    if st.session_state.debug_level_checks:
        mem = memory_summary()
        st.caption(f"RSS: {mem['rss_mb']} MB · Peak: {mem['peak_rss_mb']} MB · Headroom: {mem['headroom_mb']} MB")

# ---------- TOP/HERO ----------
st.markdown(
    """
<div class="arapai-hero">
  <div class="arapai-title">Arapai- Offline AI Tutor</div>
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
    )
    st.caption(f"Selected behavior: {LEVEL_HINTS.get(st.session_state.level, '')}")

_sync_explanation_level_change()

if st.session_state.pending_regen_all and not st.session_state.edit_mode:
    st.session_state.pending_regen_all = False
    _regenerate_all_assistant_replies()
    st.rerun()
elif st.session_state.pending_regen and not st.session_state.edit_mode:
    st.session_state.pending_regen = False
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        st.session_state.messages.pop()
    last_user = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), None)
    if last_user:
        _complete_assistant_reply(last_user)
        st.rerun()
elif pending_user := _pending_assistant_user_text():
    _complete_assistant_reply(pending_user)
    st.rerun()

if st.session_state.mode == "cbc":
    render_cbc_learn()
    st.stop()

# ---------- DISPLAY CHAT ----------
if st.session_state.get("_pending_rag_warning"):
    st.warning(st.session_state.pop("_pending_rag_warning"))

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

# ---------- SAMPLE PROMPTS ----------
if not st.session_state.edit_mode and st.session_state.mode == "chat":
    st.caption("Sample prompts")
    prompt_cols = st.columns(len(SAMPLE_PROMPTS))
    for i, sample in enumerate(SAMPLE_PROMPTS):
        if prompt_cols[i].button(f"Prompt {i + 1}", key=f"sample-{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": sample})
            st.rerun()

# ---------- INPUT ----------
if not st.session_state.edit_mode:
    if chat_value := st.chat_input("Ask Arapai"):
        st.session_state.messages.append({"role": "user", "content": chat_value})
        st.rerun()

if st.session_state.debug_level_checks and st.session_state.last_debug_info:
    st.markdown("### Debug: Level Compliance")
    st.json(st.session_state.last_debug_info)