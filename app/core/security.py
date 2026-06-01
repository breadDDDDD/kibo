"""
Input security — sanitises and validates user messages before
they reach the LLM or any tool. Lightweight, no external deps.
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Patterns that signal prompt injection attempts ─────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+)?(?!mitsubishi|parts|mechanic|workshop)",  # allow legit context
    r"new\s+instructions?\s*:",
    r"system\s*prompt\s*:",
    r"<\s*system\s*>",
    r"</?\s*instructions?\s*/?>",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(safety|instructions|rules|constraints)",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)

# ── Limits ──────────────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 500   # characters — parts queries don't need more
MAX_NEWLINES       = 5     # excessive newlines are a red flag


class InputValidationError(ValueError):
    """Raised when a message fails security validation."""
    pass


def sanitise_message(message: str) -> str:
    """
    Validates and lightly sanitises a user message.
    Raises InputValidationError if the message looks malicious.
    Returns the cleaned message string.
    """
    # 1. Strip leading/trailing whitespace
    cleaned = message.strip()

    # 2. Length check
    if len(cleaned) > MAX_MESSAGE_LENGTH:
        raise InputValidationError(
            f"Message too long ({len(cleaned)} chars). Maximum is {MAX_MESSAGE_LENGTH}."
        )

    # 3. Newline abuse check
    if cleaned.count("\n") > MAX_NEWLINES:
        raise InputValidationError("Message contains too many line breaks.")

    # 4. Null byte / control characters (except normal whitespace)
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", cleaned):
        raise InputValidationError("Message contains invalid characters.")

    # 5. Prompt injection pattern check
    if _INJECTION_RE.search(cleaned):
        logger.warning("Prompt injection attempt detected: %.80s", cleaned)
        raise InputValidationError(
            "Your message was flagged as potentially harmful. "
            "Please ask about Mitsubishi spare parts only."
        )

    return cleaned