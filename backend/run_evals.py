"""ClinicalRAG evaluation harness.

CI-friendly: set MOCK_LLM=1 (or pass --mock) to avoid Groq. Exit code 0 only
when all cases pass. Does not invent clinical validation claims — these are
regression checks against the seed corpus.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _apply_mock_flag(mock: bool) -> None:
    if mock:
        os.environ["MOCK_LLM"] = "1"
        os.environ["CLINICALRAG_MOCK_LLM"] = "1"
    # Import after env mutation so settings pick it up.
    from config import reset_settings_cache
    from rag.pipeline import reset_pipeline

    reset_settings_cache()
    reset_pipeline()


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _source_titles(sources: list[dict]) -> list[str]:
    return [source["metadata"].get("title", "") for source in sources]


def evaluate_case(case: dict) -> dict:
    from rag.pipeline import run_query

    state, latency_ms = run_query(
        query=case["query"],
        collection="clinical_guidelines",
        max_sources=4,
    )
    answer = state.get("answer", "")
    sources = state.get("relevant_docs", [])
    grounding_score = float(state.get("grounding_score", 0.0))
    refusal_reason = state.get("refusal_reason")

    checks = []
    details: dict = {}

    if case.get("expect_refusal"):
        refusal_text = "cannot find" in answer.lower() or not answer.strip()
        no_sources = len(sources) == 0
        low_grounding = grounding_score <= case.get("max_grounding", 0.1)
        expected_code = case.get("expected_refusal_reason", "off_topic")
        reason_ok = refusal_reason == expected_code
        checks.extend([refusal_text, no_sources, low_grounding, reason_ok])
        details["refusal_reason"] = refusal_reason
        details["refusal_reason_ok"] = reason_ok
    else:
        titles = " | ".join(_source_titles(sources)).lower()
        source_ok = case["expected_source"].lower() in titles
        terms_ok = _contains_any(answer, case.get("expected_terms", []))
        grounding_ok = grounding_score >= case.get("min_grounding", 0.5)
        checks.extend([source_ok, terms_ok, grounding_ok])
        details["source_ok"] = source_ok
        details["terms_ok"] = terms_ok
        details["grounding_ok"] = grounding_ok
        if case.get("expect_compound"):
            compound_ok = len(state.get("subqueries") or []) >= 2
            checks.append(compound_ok)
            details["compound_ok"] = compound_ok

    return {
        "name": case["name"],
        "passed": all(checks),
        "grounding_score": grounding_score,
        "confidence": state.get("confidence", "low"),
        "sources": _source_titles(sources),
        "latency_ms": latency_ms,
        "refusal_reason": refusal_reason,
        "citation_coverage": state.get("citation_coverage", 0.0),
        "answer_preview": answer.replace("\n", " ")[:180],
        "details": details,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ClinicalRAG eval harness")
    parser.add_argument(
        "--mock",
        "--offline",
        dest="mock",
        action="store_true",
        help="Force MOCK_LLM=1 (extractive answers, no Groq calls)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON summary to stdout",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("eval_cases.json"),
        help="Path to eval cases JSON",
    )
    args = parser.parse_args(argv)

    _apply_mock_flag(args.mock or os.getenv("MOCK_LLM", "").lower() in {"1", "true", "yes"})

    from audit.logger import init_audit_db
    from config import get_settings
    from data.seed_data import seed_if_empty
    from rag.pipeline import groq_configured

    cases = json.loads(args.cases.read_text())
    init_audit_db()
    seed_if_empty()

    settings = get_settings()
    print("ClinicalRAG eval harness")
    print(f"LLM configured: {groq_configured()} | mock_llm: {settings.mock_llm}")
    print("")

    results = [evaluate_case(case) for case in cases]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"[{status}] {result['name']} | grounding={result['grounding_score']:.2f} "
            f"| confidence={result['confidence']} | latency={result['latency_ms']}ms"
        )
        if result.get("refusal_reason"):
            print(f"      refusal: {result['refusal_reason']}")
        if result["sources"]:
            print(f"      sources: {'; '.join(result['sources'][:3])}")
        print(f"      answer: {result['answer_preview']}")

    passed = sum(1 for result in results if result["passed"])
    if args.json:
        print(
            json.dumps(
                {
                    "passed": passed,
                    "total": len(results),
                    "mock_llm": settings.mock_llm,
                    "results": results,
                },
                indent=2,
            )
        )
    else:
        print("")
        print(f"{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
