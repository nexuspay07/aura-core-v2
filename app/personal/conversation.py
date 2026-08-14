"""Small, truthful conversational boundary in front of Personal Decision V2."""

from __future__ import annotations

import re


def message_kind(message: str) -> str:
    """Distinguish social/exploratory conversation from a potential decision."""
    text = message.strip().lower()
    conversational = (
        r"^(?:hi|hello|hey|thanks|thank you)[!. ]*$",
        r"^(?:i got|i accepted|i chose|i decided|it worked|quick update)\b",
        r"^remember\b",
    )
    return "conversation" if any(re.search(pattern, text) for pattern in conversational) else "potential_decision"


def conversation_response(message: str) -> str:
    text = message.lower()
    if text.startswith("remember"):
        return "I can only revisit details that are available in this owned Aura session or in your saved Decisions. Which decision do you mean?"
    if re.search(r"\b(?:i got|i accepted|i chose|i decided|it worked)\b", text):
        return "Thanks for the update. If you want, tell me what happened and what you would like to think through next."
    return "I'm here. Tell me what's on your mind, or share a choice you want to think through."
