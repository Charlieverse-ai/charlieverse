"""Tests for charlieverse.helpers.text — text cleaning and filtering utilities."""

from __future__ import annotations

from charlieverse.helpers.text import (
    clean_text,
    is_ignored,
    strip_markdown,
    strip_noise,
    strip_punctuation,
)
from charlieverse.types.strings import CleanedText


# ---------------------------------------------------------------------------
# strip_punctuation
# ---------------------------------------------------------------------------


def test_strip_punctuation_removes_dots_and_commas():
    result = strip_punctuation("Hello, world.")
    assert "," not in result
    assert "." not in result
    assert "Hello" in result
    assert "world" in result


def test_strip_punctuation_leaves_plain_text():
    result = strip_punctuation("hello world")
    assert result == "hello world"


def test_strip_punctuation_empty():
    assert strip_punctuation("") == ""


# ---------------------------------------------------------------------------
# strip_markdown (re-exported from helpers.text)
# ---------------------------------------------------------------------------


def test_strip_markdown_removes_header():
    assert strip_markdown("# Hello") == "Hello"


def test_strip_markdown_removes_bold():
    assert strip_markdown("**bold**") == "bold"


def test_strip_markdown_empty_passthrough():
    assert strip_markdown("") == ""


# ---------------------------------------------------------------------------
# strip_noise
# ---------------------------------------------------------------------------


def test_strip_noise_removes_url():
    result = strip_noise("visit https://example.com for details")
    assert "https" not in result
    assert "example.com" not in result
    assert "visit" in result
    assert "details" in result


def test_strip_noise_removes_snake_case():
    result = strip_noise("the foo_bar_baz variable")
    # snake_case should be stripped
    assert "foo_bar_baz" not in result


def test_strip_noise_removes_uuid():
    result = strip_noise("id: 550e8400-e29b-41d4-a716-446655440000 here")
    assert "550e8400" not in result
    assert "here" in result


def test_strip_noise_collapses_extra_spaces():
    result = strip_noise("hello   world")
    assert "  " not in result


def test_strip_noise_empty():
    result = strip_noise("")
    assert result == ""


def test_strip_noise_removes_code_fences():
    result = strip_noise("before\n```python\nprint('hi')\n```\nafter")
    assert "print" not in result
    assert "before" in result
    assert "after" in result


# ---------------------------------------------------------------------------
# is_ignored
# ---------------------------------------------------------------------------


def test_is_ignored_slash_command():
    assert is_ignored("/session-save") is True


def test_is_ignored_slash_command_with_args():
    assert is_ignored("/ship patch") is True


def test_is_ignored_interrupted_request():
    assert is_ignored("[Request interrupted by user]") is True


def test_is_ignored_xml_tag_message():
    assert is_ignored("<task-notification>some task</task-notification>") is True


def test_is_ignored_normal_text():
    assert is_ignored("Hello, how are you?") is False


def test_is_ignored_empty():
    assert is_ignored("") is False


# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


def test_clean_text_returns_none_for_empty():
    assert clean_text("") is None


def test_clean_text_returns_none_for_none():
    assert clean_text(None) is None


def test_clean_text_returns_none_for_slash_command():
    assert clean_text("/session-save") is None


def test_clean_text_strips_null_bytes():
    result = clean_text("hello\x00world")
    assert result is not None
    assert "\x00" not in str(result)


def test_clean_text_returns_cleaned_text_type():
    result = clean_text("This is a normal sentence with enough words.")
    assert isinstance(result, CleanedText)


def test_clean_text_returns_cleaned_text_when_already_cleaned():
    ct = CleanedText("already clean")
    result = clean_text(ct)
    assert result is ct


def test_clean_text_returns_none_for_whitespace_only():
    assert clean_text("   \n\t  ") is None


def test_clean_text_normalizes_spaces():
    result = clean_text("hello   world")
    assert result is not None
    assert "  " not in str(result)
