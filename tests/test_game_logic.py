import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic_utils import check_guess, parse_guess, get_range_for_difficulty, update_score


def test_difficulty_ranges_scale_correctly():
    """Bug fixed: Hard (1-50) was a smaller range than Normal (1-100), making Hard easier."""
    _, easy_high = get_range_for_difficulty("Easy")
    _, normal_high = get_range_for_difficulty("Normal")
    _, hard_high = get_range_for_difficulty("Hard")

    # Each difficulty should have a wider range than the one below it
    assert easy_high < normal_high, "Normal should have a wider range than Easy"
    assert normal_high < hard_high, "Hard should have a wider range than Normal"

    # Verify exact expected values
    assert get_range_for_difficulty("Easy") == (1, 20)
    assert get_range_for_difficulty("Normal") == (1, 50)
    assert get_range_for_difficulty("Hard") == (1, 100)


def test_parse_guess_rejects_invalid_inputs():
    """Bug fixed: empty/invalid guesses were consuming an attempt before validation."""
    # Empty and None should be rejected cleanly
    ok, value, err = parse_guess("", 1, 100)
    assert ok is False and value is None and err is not None

    ok, value, err = parse_guess(None, 1, 100)
    assert ok is False and value is None and err is not None

    # Non-numeric strings
    ok, value, err = parse_guess("abc", 1, 100)
    assert ok is False and value is None and err is not None

    # "." alone is not a valid number
    ok, value, err = parse_guess(".", 1, 100)
    assert ok is False and value is None and err is not None


def test_parse_guess_validates_range():
    """Bug fixed: no range check meant guessing 50000 on Easy (1-20) was accepted."""
    # One below minimum
    ok, value, _ = parse_guess("0", 1, 20)
    assert ok is False and value is None

    # One above maximum
    ok, value, _ = parse_guess("21", 1, 20)
    assert ok is False and value is None

    # Way out of range
    ok, value, _ = parse_guess("50000", 1, 20)
    assert ok is False and value is None

    # Exact boundaries should be accepted
    ok, value, _ = parse_guess("1", 1, 20)
    assert ok is True and value == 1

    ok, value, _ = parse_guess("20", 1, 20)
    assert ok is True and value == 20

    # Float truncation should still be range-checked
    ok, value, _ = parse_guess("20.9", 1, 20)
    assert ok is True and value == 20

    ok, value, _ = parse_guess("3.9", 1, 20)
    assert ok is True and value == 3


def test_check_guess_hints_are_correct_direction():
    """Bug fixed: hints were flipped — 'Go HIGHER!' shown when guess was too high."""
    # Guess too high → should say go LOWER
    outcome, message = check_guess(60, 50)
    assert outcome == "Too High"
    assert "LOWER" in message, f"Expected 'Go LOWER!' hint, got: {message}"

    # Guess too low → should say go HIGHER
    outcome, message = check_guess(40, 50)
    assert outcome == "Too Low"
    assert "HIGHER" in message, f"Expected 'Go HIGHER!' hint, got: {message}"

    # Edge: exactly one above
    outcome, message = check_guess(51, 50)
    assert outcome == "Too High" and "LOWER" in message

    # Edge: exactly one below
    outcome, message = check_guess(49, 50)
    assert outcome == "Too Low" and "HIGHER" in message

    # Exact match
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"


def test_check_guess_string_secret_uses_numeric_comparison():
    """Bug fixed: TypeError fallback cast guess to str, causing wrong lexicographic
    comparison — e.g. '9' > '10' is True as strings but 9 < 10 as integers."""
    # 9 < 10 numerically → Too Low; but '9' > '10' lexicographically → would wrongly give Too High
    outcome, message = check_guess(9, "10")
    assert outcome == "Too Low", (
        "9 < 10 numerically — string comparison '9' > '10' would incorrectly return Too High"
    )
    assert "HIGHER" in message

    # 15 > 10 → Too High, should hold for string secret too
    outcome, message = check_guess(15, "10")
    assert outcome == "Too High" and "LOWER" in message

    # Exact match with string secret
    outcome, _ = check_guess(10, "10")
    assert outcome == "Win"


def test_update_score_too_high_is_consistent():
    """Bug fixed: 'Too High' outcome added +5 on even attempts and deducted -5 on odd,
    with no logical justification. Should always deduct 5 like 'Too Low'."""
    # Even attempt — was wrongly adding +5
    even_score = update_score(100, "Too High", 2)
    assert even_score == 95, "Too High on even attempt should deduct 5, not add 5"

    # Odd attempt
    odd_score = update_score(100, "Too High", 3)
    assert odd_score == 95

    # Parity must not affect the result
    assert even_score == odd_score, "Too High should deduct equally regardless of attempt parity"

    # Too High and Too Low should penalise equally
    too_low_score = update_score(100, "Too Low", 1)
    too_high_score = update_score(100, "Too High", 1)
    assert too_high_score == too_low_score

    # Win still awards points, decreasing with more attempts
    win_early = update_score(0, "Win", 1)
    win_late = update_score(0, "Win", 5)
    assert win_early > win_late

    # Score floor: very late win should still award at least 10
    win_floor = update_score(0, "Win", 100)
    assert win_floor == 10
