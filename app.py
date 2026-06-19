import re
import streamlit as st
from backend.llm_engine import warm_up, generate, generate_stream
from backend.online_gemma import generate as online_generate
from backend.math_engine import solve
from backend.prompt_builder import (
    LEVEL_HINTS,
    LEVEL_LABELS,
    LEVEL_ORDER,
    LEVELS,
    build_prompt,
)
from backend.rag_engine import retrieve

st.set_page_config(page_title="Arapai- Offline AI Tutor", layout="wide")


import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "cbc_content.json")

def check_answer(user_answer, correct_answers):
    import re

    def clean(text):
        return re.sub(r'[^\w\s]', '', text.lower()).split()

    user_words = set(clean(user_answer))

    best_score = 0
    for ans in correct_answers:
        ans_words = set(clean(ans))
        if len(ans_words) == 0:
            continue
        score = len(user_words & ans_words) / len(ans_words)
        best_score = max(best_score, score)

    if best_score >= 0.5:
        return "correct"
    elif best_score >= 0.3:
        return "partial"
    else:
        return "wrong"

with open(DATA_PATH, "r") as f:
    cbc_content = json.load(f)


def _inject_gemini_style(theme_mode):
    if theme_mode == "Light":
        css = """
<style>
.stApp { background: #ffffff; color: #31333f; }
section[data-testid="stSidebar"] { background: #f0f2f6; border-right: 0px solid transparent; }
section[data-testid="stSidebar"] * { color: #31333f !important; }
.arapai-hero { padding: 0.2rem 0 0.6rem 0.1rem; }
.arapai-title { font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin-bottom: .25rem; color: #000000; }
.arapai-sub { color: #555555; font-size: 1rem; }
.stSelectbox label, .stCheckbox label, .stCaption { color: #31333f !important; }
.st-emotion-cache-1y4p8pa { max-width: 900px; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #ffffff !important;
  border: 1px solid #e6e9ef !important;
  color: #31333f !important;
  border-radius: 14px !important;
}
[data-testid="stChatInput"] > div {
  border-radius: 28px !important;
  border: 1px solid #e6e9ef !important;
  background: #ffffff !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08) !important;
}
[data-testid="stChatInput"] input {
  color: #31333f !important;
}
[data-testid="stChatMessage"] { background: transparent !important; border: 0 !important; }
[data-testid="stChatMessageContent"],
[data-testid="stChatMessageContent"] p,
[data-testid="stChatMessageContent"] li {
  color: #31333f !important;
}
[data-testid="stChatMessageAvatar"] { display: none !important; }
[data-testid="stCheckbox"] label span {
  color: #31333f !important;
}

/* Reduce Streamlit chrome for a cleaner Gemini-like canvas */
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
    if st.session_state.run_mode == "Online (Gemma 1.1)":
        return online_generate(prompt + compliance_hint)
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


def _clear_cbc_feedback_state():
    st.session_state.cbc_pending_feedback = None
    st.session_state.cbc_mistake_explanation = None


def _build_cbc_mistake_user_message(question, user_answer, topic):
    return (
        f"I am working on the topic \"{topic}\".\n\n"
        f"Scenario question:\n{question}\n\n"
        f"My answer:\n{user_answer}\n\n"
        "Explain what I misunderstood in this scenario and teach me the correct concept. "
        "Use the scenario context. Do not quote a model answer word-for-word."
    )


def _generate_cbc_mistake_explanation(question, user_answer, topic):
    user_message = _build_cbc_mistake_user_message(question, user_answer, topic)
    rag_query = f"{topic}. {question}"
    retrieved_text = None
    rag_warning = None
    if st.session_state.use_rag:
        try:
            retrieved_text = retrieve(rag_query)
        except FileNotFoundError:
            rag_warning = (
                "Reference documents not indexed. Put PDFs in **data/raw_pdfs** or **data/rawpdfs**, "
                "then run: `python -m ingestion.ingest_pdf`"
            )

    history = [{"role": "user", "content": user_message}]
    prompt = build_prompt(st.session_state.level, history, retrieved_text)
    tier = st.session_state.model_tier.lower()

    try:
        if st.session_state.run_mode == "Online (Gemma 1.1)":
            raw = online_generate(prompt)
        else:
            raw = generate(prompt, model_tier=tier)
        reply, debug = _ensure_valid_reply(prompt, st.session_state.level, tier, raw)
        if rag_warning:
            debug["rag_warning"] = rag_warning
        return reply, debug
    except Exception as e:
        return _model_error_message(e), {"error": str(e)}


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
                result = check_answer(user_answer, q["answers"])
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
                    "result": result
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
    st.markdown("## Arapai- Offline AI Tutor")
    if st.button("New Chat", use_container_width=True):
       st.session_state.mode = "chat"
       st.session_state.messages = []
       st.session_state.edit_mode = False

    if st.button("CBC-Learn", use_container_width=True):
       st.session_state.mode = "cbc"
    
    st.markdown("---")
    st.caption("Offline AI Tutor")
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
    st.checkbox("Use reference documents (PDFs)", key="use_rag")
    st.markdown("---")
    st.checkbox("Debug level compliance", key="debug_level_checks")

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
                        online_generate(prompt) if st.session_state.run_mode == "Online (Gemma 1.1)" else generate(prompt, model_tier=tier),
                    )
                    st.session_state.last_debug_info = debug
                except Exception as e:
                    reply = _model_error_message(e)
                    st.session_state.last_debug_info = {"error": str(e)}
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()


if st.session_state.mode == "cbc":
    render_cbc_learn()
    st.stop()

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
                    if st.session_state.run_mode == "Online (Gemma 1.1)":
                        with st.spinner("Thinking..."):
                            raw = online_generate(prompt)
                        reply, debug = _ensure_valid_reply(prompt, st.session_state.level, tier, raw)
                        st.session_state.last_debug_info = debug
                        st.markdown(reply)
                    else:
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