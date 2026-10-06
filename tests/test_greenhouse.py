from src.greenhouse import is_us_location, matches_target_role


def test_is_us_location_returns_true_for_us_locations():
    assert is_us_location("Austin, TX") is True
    assert is_us_location("Wilmington, DE") is True
    assert is_us_location("Remote - USA") is True
    assert is_us_location("United States") is True


def test_is_us_location_returns_false_for_non_us_locations():
    assert is_us_location("Bangalore, India") is False
    assert is_us_location("London, UK") is False
    assert is_us_location("Remote") is False


def test_matches_target_role_returns_true_for_matching_titles():
    assert matches_target_role("Senior Data Scientist", ["data scientist"]) is True
    assert matches_target_role("Senior Staff Data Engineer", ["data engineer"]) is True
    assert matches_target_role("Medicinal Chemist", ["medicinal chemist"]) is True


def test_matches_target_role_returns_false_for_non_matching_titles():
    assert matches_target_role("Strategic Finance & Analytics", ["analytics"]) is False
    assert matches_target_role("Investment Banking Analyst", ["analyst"]) is False
    assert matches_target_role("Software Engineer", ["data engineer"]) is False
