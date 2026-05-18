import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from audit.logger import init_audit_db
from data.seed_data import seed_if_empty
from rag.pipeline import groq_configured, run_query


def _contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _source_titles(sources: list[dict]) -> list[str]:
    return [source["metadata"].get("title", "") for source in sources]


def evaluate_case(case: dict) -> dict:
    state, latency_ms = run_query(
        query=case["query"],
        collection="clinical_guidelines",
        max_sources=4,
    )
    answer = state.get("answer", "")
    sources = state.get("relevant_docs", [])
    grounding_score = float(state.get("grounding_score", 0.0))

    checks = []

    if case.get("expect_refusal"):
        refusal_text = "cannot find" in answer.lower() or not answer.strip()
        no_sources = len(sources) == 0
        low_grounding = grounding_score <= case.get("max_grounding", 0.1)
        checks.extend([refusal_text, no_sources, low_grounding])
    else:
        titles = " | ".join(_source_titles(sources)).lower()
        source_ok = case["expected_source"].lower() in titles
        terms_ok = _contains_any(answer, case.get("expected_terms", []))
        grounding_ok = grounding_score >= case.get("min_grounding", 0.5)
        checks.extend([source_ok, terms_ok, grounding_ok])

    return {
        "name": case["name"],
        "passed": all(checks),
        "grounding_score": grounding_score,
        "confidence": state.get("confidence", "low"),
        "sources": _source_titles(sources),
        "latency_ms": latency_ms,
        "answer_preview": answer.replace("\n", " ")[:180],
    }


def main() -> int:
    cases_path = Path(__file__).with_name("eval_cases.json")
    cases = json.loads(cases_path.read_text())

    init_audit_db()
    seed_if_empty()

    print("ClinicalRAG eval harness")
    print(f"LLM configured: {groq_configured()}")
    print("")

    results = [evaluate_case(case) for case in cases]

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"[{status}] {result['name']} | grounding={result['grounding_score']:.2f} "
            f"| confidence={result['confidence']} | latency={result['latency_ms']}ms"
        )
        if result["sources"]:
            print(f"      sources: {'; '.join(result['sources'][:3])}")
        print(f"      answer: {result['answer_preview']}")

    passed = sum(1 for result in results if result["passed"])
    print("")
    print(f"{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
