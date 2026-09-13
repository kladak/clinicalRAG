from rag.decompose import decompose_query, extract_clinical_terms


def test_extract_clinical_terms_hf_sglt2():
    terms = extract_clinical_terms(
        "What SGLT2 inhibitors are recommended for heart failure HFrEF?"
    )
    assert "sglt2" in terms
    assert "hfref" in terms or "heart" in terms


def test_compound_query_splits():
    result = decompose_query(
        "What are first-line treatments for HFrEF? And also how should sepsis be diagnosed?"
    )
    assert result.is_compound is True
    assert len(result.subqueries) >= 2
    queries = result.retrieval_queries
    assert queries[0].startswith("What are first-line")
    assert len(queries) >= 2


def test_simple_query_not_compound():
    result = decompose_query("What are the diagnostic criteria for sepsis?")
    assert result.is_compound is False
    assert result.subqueries == []
    assert "sepsis" in result.clinical_terms
