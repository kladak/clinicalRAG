import re

STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "also",
    "and",
    "are",
    "because",
    "been",
    "being",
    "between",
    "both",
    "but",
    "can",
    "for",
    "from",
    "had",
    "has",
    "have",
    "having",
    "her",
    "here",
    "him",
    "his",
    "how",
    "into",
    "its",
    "may",
    "more",
    "not",
    "only",
    "other",
    "our",
    "out",
    "over",
    "per",
    "she",
    "should",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "this",
    "those",
    "through",
    "under",
    "using",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "you",
    "your",
}


def _normalize_token(token: str) -> str:
    token = token.lower()
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    return [_normalize_token(token) for token in re.findall(r"[a-zA-Z0-9]+", text)]


def _content_tokens(text: str) -> set[str]:
    return {
        token
        for token in _tokens(text)
        if len(token) >= 3 and token not in STOPWORDS
    }


def _has_exact_ngram(sentence_tokens: list[str], combined_source: str, size: int = 4) -> bool:
    if len(sentence_tokens) < size:
        return False
    for i in range(len(sentence_tokens) - size + 1):
        if " ".join(sentence_tokens[i : i + size]) in combined_source:
            return True
    return False


def _is_grounded(sentence: str, source_token_sets: list[set[str]], combined_source: str) -> bool:
    sentence_tokens = _tokens(sentence)
    if len(sentence_tokens) < 4:
        return True

    if _has_exact_ngram(sentence_tokens, combined_source):
        return True

    content = _content_tokens(sentence)
    if not content:
        return True

    high_signal = {
        token for token in content if any(char.isdigit() for char in token) or len(token) >= 7
    }

    for source_tokens in source_token_sets:
        overlap = content & source_tokens
        overlap_ratio = len(overlap) / len(content)

        if len(content) <= 5 and len(overlap) >= 2 and overlap_ratio >= 0.5:
            return True
        if len(overlap) >= 4 and overlap_ratio >= 0.35:
            return True
        if len(overlap) >= 6 and overlap_ratio >= 0.25:
            return True
        if high_signal and len(high_signal & source_tokens) >= 3 and overlap_ratio >= 0.25:
            return True

    return False


def compute_grounding_score(answer: str, source_texts: list[str]) -> float:
    """
    Sentence-level grounding: what fraction of answer sentences can be tied
    back to at least one source chunk.

    Exact n-gram overlap is strong evidence, but clinical LLM answers often
    paraphrase. We therefore also accept substantial overlap on normalized
    content tokens inside the same source chunk.
    """
    if not answer or not source_texts:
        return 0.0

    sentences = [
        sentence.strip(" -\t")
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", answer)
        if len(sentence.strip(" -\t")) > 20
    ]
    if not sentences:
        return 0.5

    combined_sources = " ".join(_tokens(" ".join(source_texts)))
    source_token_sets = [_content_tokens(text) for text in source_texts]
    grounded = 0

    for sentence in sentences:
        if _is_grounded(sentence, source_token_sets, combined_sources):
            grounded += 1

    return round(grounded / len(sentences), 2)
