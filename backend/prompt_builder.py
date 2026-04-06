LEVEL_ORDER = (
    "basic",
    "basic_detailed",
    "standard",
    "standard_detailed",
    "advanced",
    "advanced_detailed",
)

LEVEL_LABELS = {
    "basic": "Basic - Basic",
    "basic_detailed": "Basic - Basic (Detailed)",
    "standard": "Standard - Standard",
    "standard_detailed": "Standard - Standard (Detailed)",
    "advanced": "Advanced - Advanced",
    "advanced_detailed": "Advanced - Advanced (Detailed)",
}

LEVEL_HINTS = {
    "basic": "Summary only: 1-2 short, very simple sentences (what it is).",
    "basic_detailed": "2-3 simple sentences plus one short example/context.",
    "standard": "Summary only: concise high-level paragraph (2-3 sentences).",
    "standard_detailed": "A fuller explanation with components + simple step flow.",
    "advanced": "Summary only: concise technical explanation (3-4 sentences).",
    "advanced_detailed": "Deep technical explanation with explicit step-by-step flow.",
}

LEVELS = {
    "basic": (
        "Explain what it is using very simple language. "
        "No technical terms. "
        "Use only 1 to 2 short sentences."
    ),
    "basic_detailed": (
        "Explain what it is in simple language with a little extra context. "
        "Include one simple context clue or example. "
        "Use 2 to 3 short sentences and avoid technical terms."
    ),
    "standard": (
        "Give a concise summary of what it is and high-level how it works. "
        "Use minimal technical terms. "
        "Write 2 to 3 sentences."
    ),
    "standard_detailed": (
        "Expand the standard explanation with clearer parts and simple flow. "
        "Cover what it is, key components, and a concise high-level sequence. "
        "Write 4 to 6 sentences in one cohesive paragraph."
    ),
    "advanced": (
        "Give a concise technical summary using correct terminology. "
        "Describe key system components and how they interact. "
        "Write 3 to 4 technical sentences."
    ),
    "advanced_detailed": (
        "Provide a deep technical explanation with step-by-step system flow. "
        "Include architecture, logic sequence, and component interactions in detail. "
        "Write 6 to 10 technical sentences."
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
    "basic_detailed": (
        "- Output exactly 2-3 short sentences.\n"
        "- Focus on what it is, plus one small extra context/example.\n"
        "- Keep language simple; avoid technical jargon.\n"
        "- Include a sentence starting with 'For example,'.\n"
        "- Keep answer between 40 and 80 words."
    ),
    "standard": (
        "- Output a summarized explanation in 2-3 sentences.\n"
        "- Explain what it is and high-level how it works.\n"
        "- Use only minimal technical terms.\n"
        "- Keep answer between 45 and 90 words.\n"
        "- Do not include numbered steps."
    ),
    "standard_detailed": (
        "- Output two parts:\n"
        "  Part 1: one short paragraph summary.\n"
        "  Part 2: a numbered flow with 3-4 steps.\n"
        "- Include components and a simple flow from input to output.\n"
        "- Must be more detailed than standard.\n"
        "- Keep answer between 130 and 200 words."
    ),
    "advanced": (
        "- Output a summarized technical explanation in 3-4 sentences.\n"
        "- Use correct technical terminology.\n"
        "- Explain component interactions clearly.\n"
        "- Keep answer between 70 and 130 words.\n"
        "- Do not include numbered steps."
    ),
    "advanced_detailed": (
        "- Output two parts:\n"
        "  Part 1: architecture overview paragraph.\n"
        "  Part 2: numbered step-by-step sequence with 5-8 steps.\n"
        "- Include logic sequence, architecture details, and component interactions.\n"
        "- Must be more detailed than advanced.\n"
        "- Keep answer between 220 and 340 words."
    ),
}

def build_prompt(level, history, retrieved_text=None):
    instruction = LEVELS.get(level, LEVELS["standard"])
    response_rules = RESPONSE_RULES.get(level, RESPONSE_RULES["standard"])

    prompt = f"""
You are Arapai, an offline educational research assistant.

Instruction:
{instruction}

Response rules (MUST follow):
{response_rules}

Behavior constraints (MUST follow):
- Answer directly. Do not apologize.
- Do not mention previous responses, corrections, or confusion.
- Do not say "I apologize", "Sorry", "as mentioned", or similar meta commentary.

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
