from rag.guards import (
    REFUSAL_ANSWER,
    check_answer_faithfulness,
    check_off_topic,
    unsupported_dosage_claims,
)


def test_off_topic_capital():
    decision = check_off_topic("What is the capital of France?")
    assert decision.allow is False
    assert decision.code == "off_topic"


def test_clinical_query_allowed():
    decision = check_off_topic("What SGLT2 inhibitors are recommended for heart failure?")
    assert decision.allow is True


def test_unsupported_dosage_detected():
    sources = ["Dapagliflozin 10mg daily is recommended for HFrEF."]
    answer = "Use dapagliflozin 25 mg daily for all patients."
    claims = unsupported_dosage_claims(answer, sources)
    assert any("25" in c for c in claims)


def test_supported_dosage_passes():
    sources = ["Dapagliflozin (Farxiga) 10mg daily or empagliflozin 10mg daily."]
    answer = "Dapagliflozin 10mg daily is recommended."
    assert unsupported_dosage_claims(answer, sources) == []
    decision = check_answer_faithfulness(answer, sources)
    assert decision.allow is True


def test_faithfulness_refusal_message():
    sources = ["Give fluids early in sepsis."]
    answer = "Start norepinephrine at 5 mcg/kg/min immediately."
    decision = check_answer_faithfulness(answer, sources)
    assert decision.allow is False
    assert decision.code == "unsupported_dosage"
    assert REFUSAL_ANSWER.startswith("I cannot find")
