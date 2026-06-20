"""CBC scenario scoring and mistake-explanation prompts."""
import re

from backend.prompt_builder import build_mistake_prompt


def _clean_words(text):
    return set(re.sub(r"[^\w\s]", "", (text or "").lower()).split())


def keyword_score(user_answer, correct_answers):
    user_words = _clean_words(user_answer)
    if not user_words:
        return 0.0

    best = 0.0
    for ans in correct_answers:
        ans_words = _clean_words(ans)
        if not ans_words:
            continue
        best = max(best, len(user_words & ans_words) / len(ans_words))
    return best


def _score_from_keyword(keyword):
    if keyword >= 0.5:
        return "correct"
    if keyword >= 0.3:
        return "partial"
    return "wrong"


def _llm_semantic_verdict(user_answer, correct_answers, question, generate_fn, model_tier="light"):
    """Short LLM rubric for borderline answers only (max 16 tokens)."""
    rubric = (
        "You grade a student scenario answer.\n"
        f"Question: {question}\n"
        f"Student answer: {user_answer}\n"
        f"Expected concepts: {'; '.join(correct_answers)}\n"
        "Reply with exactly one word: CORRECT, PARTIAL, or WRONG."
    )
    try:
        raw = generate_fn(rubric, max_tokens=16, model_tier=model_tier).strip().upper()
    except Exception:
        return None
    if "CORRECT" in raw and "PARTIAL" not in raw and "WRONG" not in raw:
        return "correct"
    if "PARTIAL" in raw:
        return "partial"
    if "WRONG" in raw:
        return "wrong"
    return None


def check_answer(user_answer, correct_answers, question=None, generate_fn=None, model_tier="light"):
    """
    Hybrid scoring: fast keyword match, optional LLM for borderline cases.
    """
    keyword = keyword_score(user_answer, correct_answers)
    result = _score_from_keyword(keyword)

    if generate_fn and question and 0.25 <= keyword < 0.55:
        llm_result = _llm_semantic_verdict(
            user_answer, correct_answers, question, generate_fn, model_tier=model_tier
        )
        if llm_result:
            result = llm_result

    return result, round(keyword, 3)


def build_curated_mistake_explanation(level, question, user_answer, topic, correct_answers):
    """Fast, vetted mistake feedback built from rubric answers (offline demo-safe)."""
    said = (user_answer or "").strip() or "(blank)"
    answers = [a.strip() for a in (correct_answers or []) if (a or "").strip()]
    if not answers:
        answers = ["the main concept in this scenario"]
    primary = answers[0]
    secondary = answers[1] if len(answers) > 1 else primary
    tertiary = answers[2] if len(answers) > 2 else secondary
    topic_label = (topic or "this topic").strip()

    if level == "basic":
        return (
            f'You said "{said}", but that does not explain why. '
            f"{primary.capitalize()}: {secondary}."
        )

    if level == "lower_secondary":
        return (
            f'You said "{said}", which describes what happened but not why. '
            f"The circuit is overloaded because {secondary}. "
            f"{tertiary.capitalize()}. "
            f'A better answer to remember: "{primary.capitalize()}; {secondary}."'
        )

    if level == "upper_secondary":
        return (
            f"**What you said:** \"{said}\" — this repeats what happened without explaining why.\n\n"
            f"**What's wrong or missing:** The answer should connect the scenario to {primary} "
            f"and how the system responds.\n\n"
            f"**Correct reasoning:** For the question about {topic_label}, {secondary}. "
            f"In addition, {tertiary}.\n\n"
            f"**Better answer:** \"{primary.capitalize()}. {secondary.capitalize()}. "
            f"{tertiary.capitalize()}.\""
        )

    return (
        f"**What you said:** \"{said}\"\n\n"
        f"**What's wrong or missing:** The response does not identify {primary}.\n\n"
        f"**Correct reasoning:**\n"
        f"1. Read the scenario and identify the physical/electrical change.\n"
        f"2. Link it to {secondary}.\n"
        f"3. State the protection or consequence: {tertiary}.\n"
        f"4. Give a concise corrected statement using scenario evidence.\n\n"
        f"**Better answer:** \"{primary.capitalize()}. {secondary.capitalize()}. "
        f"{tertiary.capitalize()}.\""
    )


def build_mistake_history(question, user_answer, topic, correct_answers):
    user_message = (
        f'Topic: "{topic}"\n\n'
        f"Scenario question:\n{question}\n\n"
        f"My answer:\n{user_answer or '(blank)'}\n\n"
        "Please explain my mistake using this structure:\n"
        "1) What I said or implied\n"
        "2) What is wrong or missing in my reasoning\n"
        "3) The correct reasoning for this scenario\n"
        "4) A concise corrected answer I should remember\n\n"
        "Use the scenario context. Do not scold me. Do not copy rubric phrases verbatim."
    )
    return [{"role": "user", "content": user_message}]


def build_mistake_prompt_for_level(level, question, user_answer, topic, correct_answers, retrieved_text=None):
    history = build_mistake_history(question, user_answer, topic, correct_answers)
    return build_mistake_prompt(level, history, retrieved_text)
