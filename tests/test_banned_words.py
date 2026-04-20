"""Tests for charlieverse.helpers.banned_words — phrase detection and formatting."""

from __future__ import annotations

from charlieverse.helpers.banned_words import (
    BANNED_WORDS,
    banned_word_string,
    check_text,
    format_feedback,
    sorted_banned_words,
)

# ---------------------------------------------------------------------------
# sorted_banned_words / banned_word_string
# ---------------------------------------------------------------------------


def test_sorted_banned_words_returns_alphabetical():
    result = sorted_banned_words()
    assert result == sorted(result)


def test_sorted_banned_words_covers_full_set():
    assert set(sorted_banned_words()) == BANNED_WORDS


def test_banned_word_string_wraps_each_phrase_in_quotes():
    result = banned_word_string()
    # One quoted phrase per banned word, joined by ", "
    assert result.count('"') == 2 * len(BANNED_WORDS)


def test_banned_word_string_is_stable_across_calls():
    # Sorted output means repeated calls produce the same string
    assert banned_word_string() == banned_word_string()


# ---------------------------------------------------------------------------
# check_text — basic detection
# ---------------------------------------------------------------------------


def test_check_text_empty_returns_none():
    assert check_text("") is None


def test_check_text_whitespace_only_returns_none():
    assert check_text("   \n\t  ") is None


def test_check_text_no_banned_phrase_returns_none():
    assert check_text("hello there, what's up today?") is None


def test_check_text_catches_single_banned_phrase():
    result = check_text("I can see the problem now")
    assert result is not None
    assert "I can see" in result


def test_check_text_case_insensitive():
    # BANNED_WORDS contains mixed case; input with different case should still match
    result = check_text("i can SEE the problem")
    assert result is not None
    assert "I can see" in result


def test_check_text_returns_multiple_matches():
    result = check_text("hard to believe but my gut says its fine")
    assert result is not None
    assert "hard to believe" in result
    assert "my gut says" in result


def test_check_text_dedupes_repeated_matches():
    result = check_text("worth noting, worth noting, worth noting")
    assert result == {"worth noting"}


# ---------------------------------------------------------------------------
# check_text — word-boundary matching
# ---------------------------------------------------------------------------


def test_check_text_respects_word_boundaries():
    # "root cause" is banned but "rootcause" should not match
    assert check_text("check rootcause analysis") is None


def test_check_text_matches_at_start_of_string():
    result = check_text("hard to believe but true")
    assert result is not None
    assert "hard to believe" in result


def test_check_text_matches_at_end_of_string():
    result = check_text("we need to find the root cause")
    assert result is not None
    assert "root cause" in result


# ---------------------------------------------------------------------------
# check_text — code block / quoted string exemption
# ---------------------------------------------------------------------------


def test_check_text_ignores_phrases_in_fenced_code_blocks():
    text = "```\nhard to believe this\n```"
    assert check_text(text) is None


def test_check_text_ignores_phrases_in_inline_code():
    text = "use `my gut says` as a placeholder"
    assert check_text(text) is None


def test_check_text_ignores_phrases_in_double_quotes():
    text = 'I banned the phrase "hard to believe" because it sucks'
    assert check_text(text) is None


def test_check_text_catches_phrase_outside_code_block():
    text = "```\nok\n```\nhard to believe that worked"
    result = check_text(text)
    assert result is not None
    assert "hard to believe" in result


def test_check_text_strips_code_blocks():
    """Code is always stripped - no opt-out."""
    text = "```\nhard to believe\n```"
    result = check_text(text)
    assert result is None


# ---------------------------------------------------------------------------
# format_feedback
# ---------------------------------------------------------------------------


def test_format_feedback_includes_all_matches():
    result = format_feedback({"hard to believe", "my gut says"})
    assert '"hard to believe"' in result
    assert '"my gut says"' in result


def test_format_feedback_starts_with_matched():
    result = format_feedback({"hard to believe"})
    assert result.startswith("Matched:")
