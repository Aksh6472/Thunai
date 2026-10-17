"""Deterministic hallucination check for LLM narratives (AI_DESIGN §12.5).

Every number and month name in the narrative must appear in the facts; deny-listed accusatory
terms are rejected; every cited fact id must exist. Returns a reason code, or None if it passes.
"""

import re

from app.integrations.llm.base import Draft, Fact

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_MONTHS = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)
DENY = ("fraudster", "criminal", "culprit", "accused", "guilty", "convicted", "thief", "crook")
_FACT_IDS = re.compile(r"^F\d{1,3}$")


def _numbers(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _NUMBER.findall(text):
        plain = raw.replace(",", "")
        out.add(plain.split(".")[0].lstrip("0") or "0")
    return out


def _months(text: str) -> set[str]:
    return {m.lower()[:3] for m in _MONTHS.findall(text)}


def validate(draft: Draft, facts: list[Fact]) -> str | None:
    corpus = " ".join(f.text for f in facts)
    if not draft.narrative.strip():
        return "EMPTY"
    if not (_numbers(draft.narrative) <= _numbers(corpus)):
        return "UNSUPPORTED_NUMBER"
    if not (_months(draft.narrative) <= _months(corpus)):
        return "UNSUPPORTED_DATE"
    lowered = draft.narrative.lower()
    if any(word in lowered for word in DENY):
        return "DENY_LIST"
    known = {f.id for f in facts}
    if any(not _FACT_IDS.match(i) or i not in known for i in draft.facts_used):
        return "UNKNOWN_FACT_ID"
    return None
