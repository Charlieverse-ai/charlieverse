"""Tests for markdown stripping."""

from charlieverse.nlp.markdown import strip_markdown


def test_strip_headers():
    assert strip_markdown("# Title") == "Title"
    assert strip_markdown("## Subtitle") == "Subtitle"
    assert strip_markdown("### Deep") == "Deep"


def test_strip_bold_and_italic():
    assert strip_markdown("**bold**") == "bold"
    assert strip_markdown("*italic*") == "italic"
    assert strip_markdown("***both***") == "both"
    assert strip_markdown("__bold__") == "bold"


def test_strip_code_fences():
    text = "before\n```python\nprint('hi')\n```\nafter"
    result = strip_markdown(text)
    assert "```" not in result
    assert "print('hi')" in result
    assert "before" in result
    assert "after" in result


def test_strip_inline_code():
    assert strip_markdown("use `foo()` here") == "use foo() here"


def test_strip_links():
    assert strip_markdown("[click here](https://example.com)") == "click here"


def test_strip_images():
    assert strip_markdown("![alt text](image.png)") == "alt text"


def test_strip_blockquotes():
    assert strip_markdown("> quoted text") == "quoted text"


def test_strip_unordered_lists():
    text = "- item one\n- item two\n* item three"
    result = strip_markdown(text)
    assert "item one" in result
    assert "item two" in result
    assert "item three" in result
    assert "- " not in result
    assert "* " not in result


def test_strip_ordered_lists():
    text = "1. first\n2. second"
    result = strip_markdown(text)
    assert "first" in result
    assert "second" in result
    assert "1." not in result


def test_strip_horizontal_rules():
    text = "above\n---\nbelow"
    result = strip_markdown(text)
    assert "---" not in result
    assert "above" in result
    assert "below" in result


def test_strip_strikethrough():
    assert strip_markdown("~~deleted~~") == "deleted"


def test_strip_html_tags():
    assert strip_markdown("<b>bold</b>") == "bold"
    assert strip_markdown("<charlie>content</charlie>") == "content"


def test_collapses_whitespace():
    text = "a\n\n\n\n\nb"
    result = strip_markdown(text)
    assert "\n\n\n" not in result


def test_empty_string():
    assert strip_markdown("") == ""


def test_plain_text_passthrough():
    text = "Just normal text with no markdown"
    assert strip_markdown(text) == text


def test_combined_formatting():
    text = "# Architecture\n\n**Stack**: Swift + Python\n\n- Item one\n- Item two\n\n> A quote\n\n[Link](url)"
    result = strip_markdown(text)
    assert "#" not in result
    assert "**" not in result
    assert "- " not in result
    assert ">" not in result
    assert "[" not in result
    assert "Architecture" in result
    assert "Stack" in result
    assert "Swift + Python" in result
    assert "Link" in result
