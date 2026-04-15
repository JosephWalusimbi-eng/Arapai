LEVEL_ORDER = (
    "basic",
    "lower_secondary",
    "upper_secondary",
    "technical",
)

FALLBACK_ORDER = (
    "technical",
    "upper_secondary",
    "lower_secondary",
    "basic",
)

MIGRATION_MAP = {
    "simple": "basic",
    "basic_detailed": "lower_secondary",
    "standard": "lower_secondary",
    "standard_detailed": "upper_secondary",
    "advanced": "upper_secondary",
    "advanced_detailed": "technical",
}


def migrate_legacy_explanations(legacy_payload):
    """
    Convert legacy explanation keys to the current 4-level schema.
    """
    legacy_payload = legacy_payload or {}
    migrated = {key: "" for key in LEVEL_ORDER}

    for old_key, new_key in MIGRATION_MAP.items():
        value = (legacy_payload.get(old_key) or "").strip()
        if value:
            migrated[new_key] = value

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
    requested_level = requested_level if requested_level in FALLBACK_ORDER else "lower_secondary"

    start_idx = FALLBACK_ORDER.index(requested_level)
    for level in FALLBACK_ORDER[start_idx:]:
        text = payload.get(level)
        if isinstance(text, str) and text.strip():
            return text.strip(), level

    # Absolute final fallback to never return empty.
    return "Explanation is not available.", "fallback_default"
