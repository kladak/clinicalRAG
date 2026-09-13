from rag.evaluator import compute_grounding_score


def test_grounding_high_when_paraphrase_overlaps_source():
    source = (
        "Sepsis is life-threatening organ dysfunction caused by a dysregulated "
        "host response to infection. Use SOFA score increase of 2 or more."
    )
    answer = (
        "Sepsis involves life-threatening organ dysfunction from a dysregulated "
        "host response to infection. A SOFA increase of 2 supports the diagnosis."
    )
    score = compute_grounding_score(answer, [source])
    assert score >= 0.5


def test_grounding_low_when_answer_invents_facts():
    source = "Loop diuretics are used for congestion in heart failure."
    answer = (
        "The capital of Mars is New Berlin according to planetary cardiology guidelines. "
        "Administer stardust 500 mg intravenously every hour for eternal youth."
    )
    score = compute_grounding_score(answer, [source])
    assert score <= 0.5


def test_grounding_empty_inputs():
    assert compute_grounding_score("", ["abc"]) == 0.0
    assert compute_grounding_score("some answer text here", []) == 0.0
