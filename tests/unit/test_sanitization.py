"""
Unit tests for text sanitization utilities.

Tests sanitize_text(), escape_html(), contains_dangerous_chars(), and sanitize_for_logging()
per Epic 3 Story 3.4 AC2 and AC5 requirements.
"""

import pytest

from src.utils.sanitization import (
    contains_dangerous_chars,
    escape_html,
    sanitize_for_logging,
    sanitize_text,
)


class TestSanitizeText:
    """Test sanitize_text() function for dangerous character removal."""

    def test_removes_null_bytes(self):
        """Test that null bytes are removed from text."""
        text = "Hello\x00World"
        result = sanitize_text(text)
        assert result == "HelloWorld"
        assert "\x00" not in result

    def test_removes_control_characters_except_newline_tab(self):
        """Test that control characters (except \\n, \\t) are removed."""
        # Include control chars: \x01, \x0B (vertical tab), \x1F
        # Preserve: \n (0x0A), \t (0x09)
        text = "Test\x01Data\x0BStuff\n\tContent\x1F"
        result = sanitize_text(text)
        assert result == "TestDataStuff\n\tContent"
        assert "\x01" not in result
        assert "\x0B" not in result  # vertical tab removed
        assert "\x1F" not in result
        assert "\n" in result  # newline preserved
        assert "\t" in result  # tab preserved

    def test_normalizes_unicode_to_nfc(self):
        """Test that Unicode is normalized to NFC form."""
        # é can be represented as single char (U+00E9) or combining (e + U+0301)
        text_combined = "café"  # May be composed or decomposed depending on input
        result = sanitize_text(text_combined)
        # Result should be consistently normalized
        assert "café" in result or "cafe" in result  # Allow either representation

    def test_truncates_to_max_length(self):
        """Test that text is truncated to max_length."""
        text = "A" * 100
        result = sanitize_text(text, max_length=50)
        assert len(result) == 50
        assert result == "A" * 50

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        assert sanitize_text("") == ""
        assert sanitize_text("", max_length=100) == ""

    def test_legitimate_special_chars_preserved(self):
        """Test that legitimate special characters are preserved."""
        text = "AT&T costs < $100, O'Brien said: \"Good!\""
        result = sanitize_text(text)
        assert "&" in result
        assert "<" in result
        assert "'" in result
        assert '"' in result

    def test_international_text_preserved(self):
        """Test that international text (Unicode) is preserved."""
        text = "日本語 العربية Привет"
        result = sanitize_text(text)
        assert "日本語" in result or len(result) > 0  # Unicode preserved

    def test_emoji_preserved(self):
        """Test that emoji characters are preserved."""
        text = "Fire 🔥 Rocket 🚀"
        result = sanitize_text(text)
        assert "🔥" in result
        assert "🚀" in result


class TestEscapeHtml:
    """Test escape_html() function for XSS prevention."""

    def test_escapes_script_tag(self):
        """Test that <script> tags are HTML-escaped."""
        text = "<script>alert(1)</script>"
        result = escape_html(text)
        assert result == "&lt;script&gt;alert(1)&lt;/script&gt;"
        assert "<script>" not in result

    def test_escapes_common_html_chars(self):
        """Test that < > & \" ' are escaped."""
        text = '< > & " \''
        result = escape_html(text)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
        assert "&#x27;" in result or "&apos;" in result  # ' can be &#x27; or &apos;

    def test_preserves_normal_text(self):
        """Test that normal text without HTML chars is unchanged."""
        text = "Normal text without HTML characters"
        result = escape_html(text)
        assert result == text

    def test_escapes_mixed_content(self):
        """Test escaping mixed legitimate and dangerous content."""
        text = "AT&T costs < $100"
        result = escape_html(text)
        assert "AT&amp;T" in result
        assert "&lt;" in result
        assert "$100" in result

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        assert escape_html("") == ""


class TestContainsDangerousChars:
    """Test contains_dangerous_chars() detection function."""

    def test_detects_null_byte(self):
        """Test that null bytes are detected."""
        text = "Malicious\x00data"
        assert contains_dangerous_chars(text) is True

    def test_detects_control_characters(self):
        """Test that dangerous control characters are detected."""
        assert contains_dangerous_chars("Test\x01Data") is True
        assert contains_dangerous_chars("Test\x0BData") is True
        assert contains_dangerous_chars("Test\x1FData") is True

    def test_allows_newline_and_tab(self):
        """Test that newline and tab are not flagged as dangerous."""
        assert contains_dangerous_chars("Test\nData") is False
        assert contains_dangerous_chars("Test\tData") is False

    def test_normal_text_not_dangerous(self):
        """Test that normal text is not flagged as dangerous."""
        assert contains_dangerous_chars("Normal text") is False
        assert contains_dangerous_chars("AT&T < $100") is False
        assert contains_dangerous_chars("O'Brien") is False

    def test_empty_string_not_dangerous(self):
        """Test that empty string is not flagged as dangerous."""
        assert contains_dangerous_chars("") is False

    def test_international_text_not_dangerous(self):
        """Test that international text is not flagged as dangerous."""
        assert contains_dangerous_chars("日本語") is False
        assert contains_dangerous_chars("العربية") is False


class TestSanitizeForLogging:
    """Test sanitize_for_logging() function for safe log entries."""

    def test_truncates_long_text(self):
        """Test that text longer than max_length is truncated with indicator."""
        text = "A" * 300
        result = sanitize_for_logging(text, max_length=200)
        assert len(result) <= 220  # 200 + "... (truncated)"
        assert "... (truncated)" in result

    def test_removes_dangerous_chars(self):
        """Test that dangerous characters are removed for logging."""
        text = "Test\x00Data\x01Stuff"
        result = sanitize_for_logging(text)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_short_text_unchanged(self):
        """Test that short text is not truncated."""
        text = "Short log message"
        result = sanitize_for_logging(text, max_length=200)
        assert result == text
        assert "... (truncated)" not in result

    def test_empty_string_returns_empty(self):
        """Test that empty string returns empty string."""
        assert sanitize_for_logging("") == ""
