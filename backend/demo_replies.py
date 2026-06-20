"""Curated replies for sample prompts — reliable on the Light tier."""

SAMPLE_PROMPTS = [
    "What is (48 / 6) + 7 * 2? Then explain order of operations in one sentence.",
    "A thin long wire makes a bulb dimmer than a short thick wire. Why?",
    "Explain what an open circuit means in simple terms.",
]

_DEMO_REPLIES = {
    SAMPLE_PROMPTS[1]: {
        "basic": (
            "A long thin wire has more resistance, so less current reaches the bulb and it looks dimmer. "
            "A short thick wire lets more current through."
        ),
        "lower_secondary": (
            "A longer, thinner wire has higher resistance than a short, thick one. "
            "Higher resistance reduces the current in the circuit, so the bulb receives less power and glows dimmer."
        ),
        "upper_secondary": (
            "Resistance depends on wire length and thickness: a long thin wire resists current more than a short thick wire. "
            "With the same battery voltage, less current flows through the higher-resistance path, "
            "so the bulb gets less electrical power and appears dimmer."
        ),
        "technical": (
            "A long thin conductor has higher resistance (R ~ rho*L/A), limiting current I = V/R for a fixed supply voltage. "
            "Lower current reduces bulb power P = I^2*R_bulb, producing less light.\n"
            "1. Compare path resistance: long/thin > short/thick.\n"
            "2. Apply I = V/R — higher R lowers I.\n"
            "3. Bulb power drops with current.\n"
            "4. Less power produces dimmer filament emission."
        ),
    },
    SAMPLE_PROMPTS[2]: {
        "basic": (
            "An open circuit is a break in the path, so electricity cannot flow. "
            "Nothing works until the path is complete again."
        ),
        "lower_secondary": (
            "An open circuit means the loop is broken, so current cannot flow. "
            "Examples include a switch turned off, a broken wire, or a loose connection."
        ),
        "upper_secondary": (
            "An open circuit is an incomplete conductive path in which charge carriers cannot circulate continuously. "
            "Because the loop is broken, current is effectively zero and connected devices do not operate "
            "until continuity is restored."
        ),
        "technical": (
            "An open circuit presents discontinuity in the conductive loop, so steady current cannot be sustained "
            "(I ≈ 0 under normal supply conditions).\n"
            "1. Identify the intended closed loop from source through load and return.\n"
            "2. Locate the discontinuity (switch open, fracture, loose terminal).\n"
            "3. Recognize that without a closed path, charge carriers cannot sustain net flow.\n"
            "4. Restore continuity to re-establish current and device operation."
        ),
    },
}


def get_curated_demo_reply(user_text, level):
    """Return a vetted reply for known sample prompts, or None."""
    key = (user_text or "").strip()
    replies = _DEMO_REPLIES.get(key)
    if not replies:
        return None
    return replies.get(level) or replies.get("lower_secondary")
