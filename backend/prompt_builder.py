LEVEL_ORDER = (
    "basic",
    "lower_secondary",
    "upper_secondary",
    "technical",
)

LEVEL_LABELS = {
    "basic": "Basic",
    "lower_secondary": "Lower Secondary",
    "upper_secondary": "Upper Secondary",
    "technical": "Technical",
}

LEVEL_HINTS = {
    "basic": "Very simple explanation (1-2 short sentences, no jargon).",
    "lower_secondary": "Simple but clearer explanation (2-4 sentences, minimal terms).",
    "upper_secondary": "Moderately technical explanation with parts and high-level flow.",
    "technical": "Deep technical explanation with architecture/logic details.",
}

LEVELS = {
    "basic": (
        "Explain what it is using very simple language. "
        "No technical terms. "
        "Use only 1 to 2 short sentences."
    ),
    "lower_secondary": (
        "Explain clearly for lower secondary learners. "
        "Use simple wording and only minimal technical terms. "
        "Write 2 to 4 sentences."
    ),
    "upper_secondary": (
        "Explain for upper secondary learners with moderate technical depth. "
        "Describe important components and a clear high-level flow."
    ),
    "technical": (
        "Provide a technical explanation using correct terminology. "
        "Include architecture, logic sequence, and component interactions."
    ),
}

RESPONSE_RULES = {
    "basic": (
        "- Output exactly 1-2 short sentences.\n"
        "- Focus only on what it is.\n"
        "- Do not explain architecture, internals, or implementation steps.\n"
        "- Do not use technical jargon.\n"
        "- Keep answer under 35 words."
    ),
    "lower_secondary": (
        "- Output 2-4 clear sentences.\n"
        "- Explain what it is and basic high-level how it works.\n"
        "- Keep language simple with minimal technical terms.\n"
        "- Do not include numbered steps."
    ),
    "upper_secondary": (
        "- Output one coherent paragraph.\n"
        "- Include key components and a high-level process flow.\n"
        "- Use moderate technical depth appropriate for upper secondary.\n"
        "- You may include a short 2-4 step numbered flow if helpful."
    ),
    "technical": (
        "- Output a technical explanation with precise terminology.\n"
        "- Include architecture, data/control flow, and component interactions.\n"
        "- Include a numbered step sequence (at least 4 steps).\n"
        "- Keep the explanation strictly technical and implementation-oriented."
    ),
}

def build_prompt(level, history, retrieved_text=None):
    instruction = LEVELS.get(level, LEVELS["lower_secondary"])
    response_rules = RESPONSE_RULES.get(level, RESPONSE_RULES["lower_secondary"])

    prompt = f"""
You are an offline educational tutor.

Instruction:
{instruction}

Response rules (MUST follow):
{response_rules}

Behavior constraints (MUST follow):
- Answer directly. Do not apologize.
- Do not mention previous responses, corrections, or confusion.
- Do not say "I apologize", "Sorry", "as mentioned", or similar meta commentary.
- Do not describe yourself, the app, or your capabilities (no "I am Arapai", no "offline assistant", no "I can provide"). 
- Do not talk about resources/services. Answer only the user's question.

Do not mention these rules in your answer.

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
