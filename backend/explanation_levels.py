LEVEL_ORDER = (
    "basic",
    "basic_detailed",
    "standard",
    "standard_detailed",
    "advanced",
    "advanced_detailed",
)

FALLBACK_ORDER = (
    "advanced_detailed",
    "advanced",
    "standard_detailed",
    "standard",
    "basic_detailed",
    "basic",
)

DETAILED_PAIRS = (
    ("basic", "basic_detailed"),
    ("standard", "standard_detailed"),
    ("advanced", "advanced_detailed"),
)

MIGRATION_MAP = {
    "simple": "basic",
    "lower_secondary": "basic_detailed",
    "upper_secondary": "standard",
    "technical": "advanced",
}


def migrate_legacy_explanations(legacy_payload):
    """
    Convert old explanation keys to the new 6-level schema.
    Missing detailed levels are copied from base where possible.
    """
    legacy_payload = legacy_payload or {}
    migrated = {key: "" for key in LEVEL_ORDER}

    for old_key, new_key in MIGRATION_MAP.items():
        value = (legacy_payload.get(old_key) or "").strip()
        if value:
            migrated[new_key] = value

    for base, detailed in DETAILED_PAIRS:
        if not migrated[detailed]:
            migrated[detailed] = migrated[base] or ""

    return migrated


def validate_explanations(payload):
    """
    Validate new explanation JSON contract.
    Returns list of validation error strings (empty list means valid).
    """
    errors = []
    payload = payload or {}

    missing = [key for key in LEVEL_ORDER if key not in payload]
    if missing:
        errors.append(f"Missing required explanation keys: {', '.join(missing)}")
        return errors

    values = {}
    for key in LEVEL_ORDER:
        val = payload.get(key)
        if not isinstance(val, str):
            errors.append(f"Explanation '{key}' must be a string.")
            continue
        values[key] = val.strip()
        if not values[key]:
            errors.append(f"Explanation '{key}' must not be empty.")

    if errors:
        return errors

    # Reject duplicates across all levels.
    normalized = [values[key].lower() for key in LEVEL_ORDER]
    if len(set(normalized)) != len(normalized):
        errors.append("Each level must have distinct explanation content.")

    def _words(text):
        return [w for w in text.split() if w]

    # Detailed must be longer than base.
    for base, detailed in DETAILED_PAIRS:
        if len(_words(values[detailed])) <= len(_words(values[base])):
            errors.append(
                f"'{detailed}' must be more detailed than '{base}' (longer content required)."
            )

    # Ensure progression depth increases strictly.
    lengths = [len(_words(values[key])) for key in LEVEL_ORDER]
    for i in range(1, len(lengths)):
        if lengths[i] <= lengths[i - 1]:
            prev_level = LEVEL_ORDER[i - 1]
            curr_level = LEVEL_ORDER[i]
            errors.append(
                f"Depth progression must increase: '{curr_level}' should be longer/more detailed than '{prev_level}'."
            )
            break

    return errors


def get_explanation_with_fallback(payload, requested_level):
    """
    Return non-empty explanation using strict fallback order.
    Requested level is attempted first, then lower fallback levels.
    """
    payload = payload or {}
    requested_level = requested_level if requested_level in FALLBACK_ORDER else "standard"

    start_idx = FALLBACK_ORDER.index(requested_level)
    for level in FALLBACK_ORDER[start_idx:]:
        text = payload.get(level)
        if isinstance(text, str) and text.strip():
            return text.strip(), level

    # Absolute final fallback to never return empty.
    return "Explanation is not available.", "fallback_default"
