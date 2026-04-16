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
    result = check_text("let me check the logs for you")
    assert result == {"let me check"}


def test_check_text_case_insensitive():
    # BANNED_WORDS contains lowercase; input with uppercase should still match
    result = check_text("LET ME CHECK the logs")
    assert result == {"let me check"}


def test_check_text_returns_multiple_matches():
    result = check_text("let me check and then let me explore further")
    assert result is not None
    assert "let me check" in result
    assert "let me explore" in result


def test_check_text_dedupes_repeated_matches():
    result = check_text("let me check, let me check, let me check")
    assert result == {"let me check"}


# ---------------------------------------------------------------------------
# check_text — word-boundary matching
# ---------------------------------------------------------------------------


def test_check_text_respects_word_boundaries():
    # "classic" is banned but "classical" should not match it
    assert check_text("I love classical music") is None


def test_check_text_matches_at_start_of_string():
    result = check_text("classic mistake")
    assert result == {"classic"}


def test_check_text_matches_at_end_of_string():
    result = check_text("that was a classic")
    assert result == {"classic"}


# ---------------------------------------------------------------------------
# check_text — code block / quoted string exemption
# ---------------------------------------------------------------------------


def test_check_text_ignores_phrases_in_fenced_code_blocks():
    text = "```\nlet me check the value\n```"
    assert check_text(text) is None


def test_check_text_ignores_phrases_in_inline_code():
    text = "use `let me check` as a placeholder"
    assert check_text(text) is None


def test_check_text_ignores_phrases_in_double_quotes():
    text = 'I banned the phrase "let me check" because it sucks'
    assert check_text(text) is None


def test_check_text_catches_phrase_outside_code_block():
    text = "```\nok\n```\nlet me check that for you"
    result = check_text(text)
    assert result == {"let me check"}


def test_check_text_ignore_code_false_catches_phrase_in_code():
    text = "```\nlet me check\n```"
    result = check_text(text, ignore_code=False)
    assert result == {"let me check"}


# ---------------------------------------------------------------------------
# format_feedback
# ---------------------------------------------------------------------------


def test_format_feedback_includes_all_matches():
    result = format_feedback({"classic", "let me check"})
    assert '"classic"' in result
    assert '"let me check"' in result


def test_format_feedback_starts_with_rephrase_instruction():
    result = format_feedback({"classic"})
    assert result.startswith("Rephrase without using:")
