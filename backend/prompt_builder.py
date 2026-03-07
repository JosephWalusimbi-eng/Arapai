LEVELS = {
    "Simple English": (
        "Explain in very simple English. "
        "Assume little prior knowledge. "
        "Use short sentences and examples."
    ),
    "Lower Secondary": (
        "Explain clearly for lower secondary students. "
        "Build from fundamentals."
    ),
    "Upper Secondary": (
        "Explain with moderate technical depth. "
        "Assume foundational knowledge."
    ),
    "Technical": (
        "Use technical language, precise definitions, "
        "and formal explanations."
    )
}

def build_prompt(level, history, retrieved_text=None):
    instruction = LEVELS[level]

    prompt = f"""
You are Arapai, an offline educational research assistant.

Instruction:
{instruction}

"""

    if retrieved_text:
        prompt += f"Reference Material:\n{retrieved_text}\n\n"

    prompt += "Conversation:\n"

    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = (msg.get("content") or "").strip()
        prompt += f"{role}: {content}\n"

    prompt += "Assistant:"
    return prompt
