"""Offline unit tests for refusal / dosage faithfulness guards."""

from rag.guards import (
    REFUSAL_ANSWER,
    check_answer_faithfulness,
    check_off_topic,
    is_likely_clinical_query,
    unsupported_dosage_claims,
)


def test_off_topic_capital_refused():
    decision = check_off_topic("What is the capital of France?")
    assert decision.allow is False
    assert decision.code == "off_topic"


def test_clinical_hfref_allowed():
    decision = check_off_topic("What are first-line treatments for HFrEF?")
    assert decision.allow is True


def test_non_clinical_short_query_refused():
    decision = check_off_topic("Tell me a joke please")
    assert decision.allow is False


def test_is_likely_clinical_detects_lexicon_terms():
    assert is_likely_clinical_query("SGLT2 inhibitors in heart failure")
    assert not is_likely_clinical_query("favorite color blue")


def test_unsupported_dosage_flagged_when_missing_from_sources():
    answer = "Start widgetolol at 999 mg twice daily for HFrEF."
    sources = [
        "Sacubitril/valsartan target dose is 97 mg/valsartan 103 mg twice daily."
    ]
    claims = unsupported_dosage_claims(answer, sources)
    assert any("999" in c for c in claims)
    decision = check_answer_faithfulness(answer, sources)
    assert decision.allow is False
    assert decision.code == "unsupported_dosage"


def test_supported_dosage_passes():
    answer = "Target dose: sacubitril 97 mg/valsartan 103 mg twice daily."
    sources = [
        "Target dose: sacubitril 97mg/valsartan 103mg twice daily for ambulatory HFrEF."
    ]
    assert unsupported_dosage_claims(answer, sources) == []
    assert check_answer_faithfulness(answer, sources).allow is True


def test_refusal_answer_constant_is_explicit():
    assert "cannot find" in REFUSAL_ANSWER.lower()
