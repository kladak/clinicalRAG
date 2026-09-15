from rag.decompose import decompose_query, extract_clinical_terms


def test_extract_clinical_terms_hfref():
    terms = extract_clinical_terms("What are first-line treatments for HFrEF and SGLT2?")
    assert "hfref" in terms
    assert "sglt2" in terms


def test_compound_split():
    decomposed = decompose_query(
        "What are first-line treatments for HFrEF? Also which SGLT2 inhibitors are recommended?"
    )
    assert decomposed.is_compound is True
    assert len(decomposed.subqueries) >= 2
    assert decomposed.original.startswith("What are first-line")


def test_compound_split_and_which():
    decomposed = decompose_query(
        "What are first-line treatments for HFrEF and which SGLT2 inhibitors are recommended?"
    )
    assert decomposed.is_compound is True
    assert decomposed.subqueries == [
        "What are first-line treatments for HFrEF?",
        "which SGLT2 inhibitors are recommended?",
    ]


def test_retrieval_queries_include_boost():
    decomposed = decompose_query("How should atrial fibrillation stroke risk be assessed with CHA2DS2-VASc?")
    queries = decomposed.retrieval_queries
    assert queries[0].lower().startswith("how should atrial")
    assert any("cha2ds2" in q or "fibrillation" in q for q in queries)


def test_short_non_compound_stays_single():
    decomposed = decompose_query("What are diagnostic criteria for sepsis?")
    assert decomposed.is_compound is False
    assert decomposed.subqueries == []
    assert "sepsis" in decomposed.clinical_terms
