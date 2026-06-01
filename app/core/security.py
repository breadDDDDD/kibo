"""
Input security — sanitises and validates user messages before
they reach the LLM or any tool. Lightweight, no external deps.
"""
import re
import logging

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+)?(?!mitsubishi|parts|mechanic|workshop)",
    r"new\s+instructions?\s*:",
    r"system\s*prompt\s*:",
    r"<\s*system\s*>",
    r"</?\s*instructions?\s*/?>",
    r"jailbreak",
    r"dan\s+mode",
    r"developer\s+mode",
    r"override\s+(safety|instructions|rules|constraints)",
    # Tool call injection — trying to fake tool responses in the message
    r"function_response",
    r"function_call",
    r"tool_result",
    r"\bget_stock_by_part_id\b",
    r"\bsearch_parts_catalog\b",
    # Prompt leaking attempts
    r"repeat\s+(your\s+)?(system\s+)?prompt",
    r"print\s+(your\s+)?(system\s+)?prompt",
    r"what\s+(are\s+)?your\s+instructions",
    r"reveal\s+(your\s+)?(instructions|prompt|rules)",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS),
    re.IGNORECASE,
)

MAX_MESSAGE_LENGTH = 5000
MAX_NEWLINES       = 5


class InputValidationError(ValueError):
    pass


def sanitise_message(message: str) -> str:
    cleaned = message.strip()

    if len(cleaned) > MAX_MESSAGE_LENGTH:
        raise InputValidationError(
            f"Message too long ({len(cleaned)} chars). Maximum is {MAX_MESSAGE_LENGTH}."
        )

    if cleaned.count("\n") > MAX_NEWLINES:
        raise InputValidationError("Message contains too many line breaks.")

    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", cleaned):
        raise InputValidationError("Message contains invalid characters.")

    if _INJECTION_RE.search(cleaned):
        logger.warning("Prompt injection attempt detected: %.80s", cleaned)
        raise InputValidationError(
            "Your message was flagged as potentially harmful. "
            "Please ask about Mitsubishi spare parts only."
        )

    return cleaned