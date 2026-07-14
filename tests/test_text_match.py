from cost_of_vacancy.text_match import find_column, name_matches


def test_name_matches_ignores_common_hospital_suffixes():
    assert name_matches("Springfield General Hospital", "Springfield General Hospital")
    assert name_matches("Springfield General Hospital", "SPRINGFIELD GENERAL HOSPITAL, INC.")


def test_name_matches_rejects_different_hospitals():
    assert not name_matches("Springfield General Hospital", "Riverside Medical Center")


def test_name_matches_empty_candidate():
    assert not name_matches("Springfield General Hospital", "")


def test_find_column_exact_case_insensitive():
    assert find_column(["Rndrng_NPI", "Tot_Mdcr_Pymt_Amt"], "npi") == "Rndrng_NPI"


def test_find_column_substring_fallback():
    assert find_column(["rendering_npi_number"], "npi") == "rendering_npi_number"


def test_find_column_no_match_returns_none():
    assert find_column(["foo", "bar"], "npi") is None
