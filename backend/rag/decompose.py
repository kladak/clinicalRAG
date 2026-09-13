"""Deterministic query decomposition for clinical guideline questions.

No LLM required. Splits compound questions, extracts high-signal clinical
terms, and produces retrieval variants so a single physician question can
pull the right guideline chunks even when it mixes topics (e.g. HFrEF + SGLT2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Lightweight clinical lexicon — not exhaustive; tuned to the seed corpus.
CLINICAL_TERMS = {
    "hfref",
    "hfpef",
    "hfmref",
    "heart",
    "failure",
    "sglt2",
    "dapagliflozin",
    "empagliflozin",
    "sacubitril",
    "valsartan",
    "arni",
    "ace",
    "beta",
    "blocker",
    "spironolactone",
    "eplerenone",
    "sepsis",
    "septic",
    "sofa",
    "qsofa",
    "lactate",
    "norepinephrine",
    "vasopressor",
    "atrial",
    "fibrillation",
    "cha2ds2",
    "vasc",
    "anticoagulation",
    "apixaban",
    "rivaroxaban",
    "warfarin",
    "heparin",
    "enoxaparin",
    "covid",
    "nirmatrelvir",
    "paxlovid",
    "remdesivir",
    "dexamethasone",
    "who",
    "essential",
    "medicines",
}

SPLIT_PATTERNS = [
    r"\?\s+",
    r"\band\s+also\b",
    r"\bas\s+well\s+as\b",
    r";\s+",
]


@dataclass
class DecomposedQuery:
    original: str
    subqueries: list[str] = field(default_factory=list)
    clinical_terms: list[str] = field(default_factory=list)
    is_compound: bool = False

    @property
    def retrieval_queries(self) -> list[str]:
        """Queries to embed/search — original first, then focused variants."""
        seen: set[str] = set()
        ordered: list[str] = []
        for q in [self.original, *self.subqueries]:
            key = q.strip().lower()
            if key and key not in seen:
                seen.add(key)
                ordered.append(q.strip())
        # Term-focused boost query when we have enough signal.
        if len(self.clinical_terms) >= 2:
            boost = " ".join(self.clinical_terms[:6])
            if boost.lower() not in seen:
                ordered.append(boost)
        return ordered


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def extract_clinical_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
    found: list[str] = []
    seen: set[str] = set()
    # Prefer multi-token clinical phrases already in lexicon as single tokens.
    for token in tokens:
        if token in CLINICAL_TERMS and token not in seen:
            seen.add(token)
            found.append(token)
    # CHA2DS2-VASc style hyphenated tokens
    for match in re.findall(r"cha2ds2-?vasc", query.lower()):
        if "cha2ds2" not in seen:
            found.append("cha2ds2")
            seen.add("cha2ds2")
        if "vasc" not in seen:
            found.append("vasc")
            seen.add("vasc")
    return found


def _split_compound(query: str) -> list[str]:
    parts = [query]
    for pattern in SPLIT_PATTERNS:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
        parts = next_parts
    cleaned = [_normalize(p) for p in parts if _normalize(p)]
    # Drop fragments that are too short to retrieve usefully.
    return [p if p.endswith("?") else p for p in cleaned if len(p) >= 12]


def decompose_query(query: str) -> DecomposedQuery:
    original = _normalize(query)
    terms = extract_clinical_terms(original)
    subqueries = _split_compound(original)
    # If split did nothing useful, keep single query.
    if len(subqueries) <= 1:
        subqueries = []
        is_compound = False
    else:
        is_compound = True
        # Ensure each subquery ends as a question when the original did.
        if original.endswith("?"):
            subqueries = [s if s.endswith("?") else f"{s}?" for s in subqueries]

    return DecomposedQuery(
        original=original,
        subqueries=subqueries,
        clinical_terms=terms,
        is_compound=is_compound,
    )
