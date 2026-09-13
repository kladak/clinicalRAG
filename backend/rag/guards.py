"""Lexical off-topic and unsupported-dosage heuristics for educational CDS.

These are narrow regex/allowlist checks — not a general hallucination model
and not a substitute for clinical validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag.decompose import extract_clinical_terms


OFF_TOPIC_PATTERNS = [
    r"\bcapital of\b",
    r"\bweather\b",
    r"\bmovie\b",
    r"\brecipe\b",
    r"\bjoke\b",
    r"\bstock price\b",
    r"\bwho won the\b",
    r"\bwrite (me )?a poem\b",
]

# Words that usually indicate a clinical intent even without lexicon hits.
CLINICAL_INTENT_HINTS = {
    "patient",
    "dose",
    "dosage",
    "treatment",
    "therapy",
    "guideline",
    "diagnosis",
    "diagnostic",
    "criteria",
    "symptom",
    "hospital",
    "icu",
    "mg",
    "contraindication",
    "indication",
    "protocol",
}

DOSAGE_CLAIM = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|mL|units?|IU)\b",
    re.IGNORECASE,
)


@dataclass
class GuardDecision:
    allow: bool
    reason: str | None = None
    code: str | None = None


def is_likely_clinical_query(query: str) -> bool:
    terms = extract_clinical_terms(query)
    if terms:
        return True
    tokens = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    if tokens & CLINICAL_INTENT_HINTS:
        return True
    return False


def check_off_topic(query: str) -> GuardDecision:
    lowered = query.lower()
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, lowered):
            return GuardDecision(
                allow=False,
                reason=(
                    "This question does not appear to be about the ingested clinical "
                    "guidelines. ClinicalRAG only answers from the local guideline corpus."
                ),
                code="off_topic",
            )
    if not is_likely_clinical_query(query):
        return GuardDecision(
            allow=False,
            reason=(
                "No clinical intent detected for the available guideline collection. "
                "Please ask a guideline-oriented question or ingest relevant documents."
            ),
            code="non_clinical",
        )
    return GuardDecision(allow=True)


def unsupported_dosage_claims(answer: str, source_texts: list[str]) -> list[str]:
    """Return dosage strings in the answer that never appear in sources."""
    if not answer:
        return []
    combined = " ".join(source_texts).lower()
    claims: list[str] = []
    for match in DOSAGE_CLAIM.finditer(answer):
        claim = match.group(0)
        # Normalize spacing for containment check.
        needle = re.sub(r"\s+", " ", claim.lower())
        compact_source = re.sub(r"\s+", " ", combined)
        if needle not in compact_source:
            # Also try without space: "10mg"
            nospace = needle.replace(" ", "")
            if nospace not in compact_source.replace(" ", ""):
                claims.append(claim)
    return claims


def check_answer_faithfulness(answer: str, source_texts: list[str]) -> GuardDecision:
    if not answer.strip():
        return GuardDecision(allow=True)
    unsupported = unsupported_dosage_claims(answer, source_texts)
    if unsupported:
        return GuardDecision(
            allow=False,
            reason=(
                "Answer contained dosage claims not present in retrieved guidelines "
                f"({', '.join(unsupported[:3])}). Refusing to present an ungrounded dose."
            ),
            code="unsupported_dosage",
        )
    return GuardDecision(allow=True)


REFUSAL_ANSWER = (
    "I cannot find this in the available guidelines. "
    "Please verify with primary clinical sources."
)
