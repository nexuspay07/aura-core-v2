"""Narrow deterministic safety boundary for the Personal Ask surface."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PersonalSafetyResponse:
    category: str
    severity: str
    message: str

    @property
    def mode(self) -> str:
        return "SAFETY_IMMEDIATE" if self.severity == "immediate" else "SAFETY_HIGH_STAKES"


_CHEST_BREATHING_EMERGENCY = re.compile(
    r"\b(?:severe|sudden|crushing)?\s*chest pain\b.{0,100}\b(?:can(?:not|'t) breathe|difficulty breathing|shortness of breath)\b"
    r"|\b(?:can(?:not|'t) breathe|difficulty breathing|shortness of breath)\b.{0,100}\b(?:severe|sudden|crushing)?\s*chest pain\b",
    re.I,
)
_OTHER_MEDICAL_EMERGENCY = re.compile(
    r"\b(?:i think i(?:'m| am) having a stroke|(?:collapsed|fainted) and (?:is not|isn't) (?:responding|breathing)|unconscious and (?:not|isn't) responding)\b",
    re.I,
)
_SELF_HARM = re.compile(
    r"\b(?:i (?:am|'m) going to kill myself|i (?:want|plan|intend) to (?:kill|hurt) myself|"
    r"i have a plan to (?:kill|hurt) myself|i (?:am|'m) going to end my life|i plan to die by suicide)\b",
    re.I,
)
_DANGEROUS_FACILITATION = re.compile(
    r"\b(?:how (?:do|can) i|tell me how to|best way to|help me|instructions? (?:for|to))\b"
    r".{0,100}\b(?:kill|seriously injure|poison|set fire to|make a bomb|build a bomb)\b"
    r".{0,50}\b(?:someone|a person|people|a building|their home|without getting caught)?",
    re.I,
)
_CRITICAL_LEGAL = re.compile(
    r"\b(?:served (?:with )?(?:court )?papers|court (?:papers|order|summons|deadline)|legal deadline)\b"
    r".{0,140}\b(?:today|tomorrow|immediately|ignore|miss(?:ed)?|deadline)\b"
    r"|\b(?:for certain|guarantee|guaranteed)\b.{0,80}\b(?:contract|legal rights?)\b.{0,80}\b(?:protects?|win|safe)\b",
    re.I,
)
_GUARANTEED_FINANCE = re.compile(
    r"\b(?:guarantee(?:d)?|for certain|exactly)\b.{0,100}\b(?:stock|investment|crypto|return|double my money|profit)\b"
    r"|\b(?:which|what)\s+(?:stock|investment|crypto)\b.{0,100}\b(?:guarantee(?:d)?|double my money|cannot lose|can't lose)\b",
    re.I,
)


class PersonalSafetyBoundary:
    """Intercept only obvious launch-critical cases without a provider call."""

    def evaluate(self, message: str) -> PersonalSafetyResponse | None:
        text = " ".join(message.strip().split())[:12000]
        if _SELF_HARM.search(text):
            return PersonalSafetyResponse(
                "self_harm", "immediate",
                "I'm really sorry you're in immediate danger. Please move away from anything you could use to hurt yourself and contact local emergency services or a crisis service now. If you can, call or go to a trusted person and tell them plainly that you may hurt yourself; do not stay alone. I haven't contacted anyone for you.",
            )
        if _CHEST_BREATHING_EMERGENCY.search(text) or _OTHER_MEDICAL_EMERGENCY.search(text):
            return PersonalSafetyResponse(
                "medical_emergency", "immediate",
                "This could be a medical emergency. Contact local emergency services now. If someone is with you, ask them to call and stay with you; do not drive yourself if you are severely unwell. Aura cannot diagnose this or contact help for you.",
            )
        if _DANGEROUS_FACILITATION.search(text):
            return PersonalSafetyResponse(
                "dangerous_conduct", "immediate",
                "I can't help plan or optimize conduct that could seriously harm someone. If there is an immediate risk, move away from weapons or dangerous materials and contact local emergency services. I can help with de-escalation, leaving safely, or general harm-prevention information.",
            )
        if _CRITICAL_LEGAL.search(text):
            return PersonalSafetyResponse(
                "critical_legal", "high_stakes",
                "Do not assume a court or legal deadline can safely be ignored. I can help you organize the papers and questions, but I cannot determine your rights or guarantee the outcome. Preserve every document, note the stated deadline, and contact a qualified lawyer, legal-aid service, or the court office as soon as possible.",
            )
        if _GUARANTEED_FINANCE.search(text):
            return PersonalSafetyResponse(
                "speculative_finance", "high_stakes",
                "No stock or speculative investment can be identified as a guaranteed short-term winner. I won't invent certainty. I can help compare downside risk, time horizon, diversification, fees, and how much loss you could withstand; avoid committing money needed for essential expenses based on a promised return.",
            )
        return None


personal_safety_boundary = PersonalSafetyBoundary()
