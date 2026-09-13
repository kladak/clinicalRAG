from rag.citations import annotate_citations, citation_coverage


def test_annotate_maps_sentence_to_matching_title():
    docs = [
        {
            "content": (
                "Dapagliflozin 10mg daily or empagliflozin 10mg daily reduce "
                "risk of CV death and worsening heart failure."
            ),
            "metadata": {"title": "AHA/ACC 2022 Heart Failure Management Guidelines"},
        }
    ]
    answer = (
        "Dapagliflozin or empagliflozin are recommended to reduce worsening "
        "heart failure risk in appropriate patients."
    )
    cites = annotate_citations(answer, docs)
    assert cites
    assert cites[0].grounded is True
    assert "Heart Failure" in cites[0].source_titles[0]
    assert citation_coverage(cites) == 1.0


def test_ungrounded_sentence_has_empty_titles():
    docs = [
        {
            "content": "Warfarin remains on the WHO essential medicines list.",
            "metadata": {"title": "WHO Anticoagulants"},
        }
    ]
    answer = "Unrelated planetary cardiology requires starlight infusion protocols today."
    cites = annotate_citations(answer, docs)
    assert cites
    assert cites[0].grounded is False
