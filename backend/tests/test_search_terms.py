from app.services.search_terms import expand_title_terms, opportunity_types_for


def test_learnership_plural_and_typo_expand_to_the_same_words():
    assert "learnership" in expand_title_terms("learnerships")
    assert "learnerships" in expand_title_terms("lernership")
    assert opportunity_types_for("learnerships") == ["learnership"]
    assert opportunity_types_for("lernership") == ["learnership"]


def test_a_mixed_phrase_does_not_match_every_role_of_that_type():
    assert opportunity_types_for("nurse learnership") == []
    terms = expand_title_terms("nurse learnership")
    assert "nurse learnership" in terms
    assert "nurse learnerships" in terms


def test_graduate_programme_spelling():
    assert opportunity_types_for("graduate program") == ["graduate_programme"]
    assert "graduate programme" in expand_title_terms("graduate program")
