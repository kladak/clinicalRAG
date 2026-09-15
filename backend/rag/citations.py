"""Per-sentence source attribution helpers.

Map answer sentences back to retrieved chunks so the API can return
overlap-based source titles. `grounded` means attribution overlap met a
minimum ratio, aligned with the evaluator's content-token thresholds rather than a
clinical faithfulness certificate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag.evaluator import _content_tokens, _tokens


@dataclass
class SentenceCitation:
    sentence: str
    source_titles: list[str]
    grounded: bool


def split_answer_sentences(answer: str) -> list[str]:
    return [
        sentence.strip(" -\t")
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer)
        if len(sentence.strip(" -\t")) > 15
    ]


# Keep citation "grounded" aligned with evaluator content-token bar.
_MIN_ATTRIBUTION_RATIO = 0.30


def _best_source_titles(
    sentence: str, docs: list[dict], top_n: int = 2, min_ratio: float = _MIN_ATTRIBUTION_RATIO
) -> list[str]:
    content = _content_tokens(sentence)
    if not content:
        return []
    scored: list[tuple[float, str]] = []
    for doc in docs:
        source_tokens = _content_tokens(doc.get("content", ""))
        overlap = content & source_tokens
        if not overlap:
            continue
        ratio = len(overlap) / max(len(content), 1)
        if ratio < min_ratio:
            continue
        title = doc.get("metadata", {}).get("title", "Unknown")
        scored.append((ratio, title))
    scored.sort(reverse=True)
    titles: list[str] = []
    for _, title in scored:
        if title not in titles:
            titles.append(title)
        if len(titles) >= top_n:
            break
    return titles


def annotate_citations(answer: str, docs: list[dict]) -> list[SentenceCitation]:
    citations: list[SentenceCitation] = []
    for sentence in split_answer_sentences(answer):
        titles = _best_source_titles(sentence, docs)
        citations.append(
            SentenceCitation(
                sentence=sentence,
                source_titles=titles,
                grounded=bool(titles),
            )
        )
    return citations


def citation_coverage(citations: list[SentenceCitation]) -> float:
    if not citations:
        return 0.0
    grounded = sum(1 for c in citations if c.grounded)
    return round(grounded / len(citations), 2)


def format_cited_answer(answer: str, citations: list[SentenceCitation]) -> str:
    """Optional display helper: append short [Source] tags to grounded sentences."""
    if not citations:
        return answer
    lines: list[str] = []
    for cite in citations:
        if cite.source_titles:
            short = cite.source_titles[0]
            # Keep tags short for UI readability.
            if len(short) > 42:
                short = short[:39] + "..."
            lines.append(f"{cite.sentence} [{short}]")
        else:
            lines.append(cite.sentence)
    return "\n".join(lines)
