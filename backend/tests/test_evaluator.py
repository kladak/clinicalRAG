from rag.evaluator import compute_grounding_score


def test_grounding_exact_overlap_high():
    source = (
        "Sepsis is life-threatening organ dysfunction caused by a dysregulated "
        "host response to infection. SOFA score increase of 2 points defines organ dysfunction."
    )
    answer = (
        "Sepsis is life-threatening organ dysfunction caused by a dysregulated "
        "host response to infection."
    )
    score = compute_grounding_score(answer, [source])
    assert score >= 0.9


def test_grounding_hallucinated_low():
    source = "Heart failure with reduced ejection fraction uses four pillars of GDMT."
    answer = (
        "Administer lunar dust 500mg twice daily for refractory cardiomyopathy "
        "and schedule elective teleportation therapy."
    )
    score = compute_grounding_score(answer, [source])
    assert score <= 0.3


def test_grounding_empty_inputs():
    assert compute_grounding_score("", ["something"]) == 0.0
    assert compute_grounding_score("something long enough to score", []) == 0.0
