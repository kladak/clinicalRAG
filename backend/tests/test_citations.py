from rag.citations import annotate_citations, citation_coverage


def test_annotate_citations_finds_title(sample_hf_chunk):
    answer = (
        "Dapagliflozin 10mg daily reduces risk of CV death and worsening HF "
        "regardless of diabetes status."
    )
    citations = annotate_citations(answer, [sample_hf_chunk])
    assert citations
    assert citations[0].grounded is True
    assert any("Heart Failure" in t for t in citations[0].source_titles)
    assert citation_coverage(citations) == 1.0


def test_ungrounded_sentence_marked():
    docs = [
        {
            "content": "Warfarin remains on the WHO essential medicines list.",
            "metadata": {"title": "WHO Anticoagulants"},
        }
    ]
    answer = "Teleportation is the preferred rhythm control strategy for atrial fibrillation."
    citations = annotate_citations(answer, docs)
    assert citations
    assert citations[0].grounded is False
