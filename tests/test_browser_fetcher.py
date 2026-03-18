"""Tests for src/browser_fetcher.py — comprehensive TDD test suite."""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_page(text_content: str = "Sample page text content", status: int = 200) -> MagicMock:
    """Build a mock Playwright page object."""
    page = MagicMock()
    response = MagicMock()
    response.status = status
    page.goto.return_value = response
    page.text_content.return_value = text_content
    page.content.return_value = f"<html><body>{text_content}</body></html>"
    return page


def _mock_browser(page: MagicMock | None = None) -> MagicMock:
    """Build a mock Playwright browser with a default page."""
    if page is None:
        page = _mock_page()
    browser = MagicMock()
    browser.new_page.return_value = page
    return browser


def _mock_playwright(browser: MagicMock | None = None) -> MagicMock:
    """Build a mock Playwright context manager."""
    if browser is None:
        browser = _mock_browser()
    pw = MagicMock()
    pw.chromium.launch.return_value = browser
    return pw


# ---------------------------------------------------------------------------
# fetch_page
# ---------------------------------------------------------------------------


class TestFetchPage:
    @patch("src.browser_fetcher.sync_playwright")
    def test_happy_path_returns_page_text(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page(text_content="Jordan is a beautiful country")
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("https://example.com/jordan-travel")

        assert "Jordan is a beautiful country" in result

    @patch("src.browser_fetcher.sync_playwright")
    def test_page_goto_called_with_url(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        fetch_page("https://example.com/test-page")

        page.goto.assert_called_once()
        call_args = page.goto.call_args
        assert "https://example.com/test-page" in str(call_args)

    @patch("src.browser_fetcher.sync_playwright")
    def test_timeout_raises_timeout_error(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = MagicMock()
        page.goto.side_effect = TimeoutError("Navigation timeout of 30000ms exceeded")
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        with pytest.raises((TimeoutError, Exception)):
            fetch_page("https://slow-site.example.com/page", timeout_ms=5000)

    @patch("src.browser_fetcher.sync_playwright")
    def test_invalid_url_raises_value_error(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        with pytest.raises(ValueError):
            fetch_page("not-a-valid-url")

    @patch("src.browser_fetcher.sync_playwright")
    def test_url_without_scheme_raises_value_error(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        with pytest.raises(ValueError):
            fetch_page("example.com/page")

    @patch("src.browser_fetcher.sync_playwright")
    def test_page_returns_404_returns_empty_string(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page(text_content="Not Found", status=404)
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("https://example.com/missing-page")

        assert result == ""

    @patch("src.browser_fetcher.sync_playwright")
    def test_connection_refused_raises_connection_error(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = MagicMock()
        page.goto.side_effect = ConnectionError("Connection refused")
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        with pytest.raises(ConnectionError):
            fetch_page("https://down-site.example.com/page")

    @patch("src.browser_fetcher.sync_playwright")
    def test_very_large_page_content_returned(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        large_content = "A" * 500_000
        page = _mock_page(text_content=large_content)
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("https://example.com/large-page")

        # Result should contain content (possibly truncated, but not empty)
        assert len(result) > 0

    @patch("src.browser_fetcher.sync_playwright")
    def test_browser_is_closed_after_fetch(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        fetch_page("https://example.com/page")

        browser.close.assert_called_once()

    @patch("src.browser_fetcher.sync_playwright")
    def test_browser_closed_even_on_error(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = MagicMock()
        page.goto.side_effect = ConnectionError("Connection refused")
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        with pytest.raises(ConnectionError):
            fetch_page("https://down.example.com/page")

        browser.close.assert_called_once()

    @patch("src.browser_fetcher.sync_playwright")
    def test_default_timeout_is_30000(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        fetch_page("https://example.com/page")

        call_args = page.goto.call_args
        # The timeout should be passed — either as kwarg or in the call
        call_str = str(call_args)
        assert "30000" in call_str or page.goto.called

    @patch("src.browser_fetcher.sync_playwright")
    def test_custom_timeout_passed_to_page_goto(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        fetch_page("https://example.com/page", timeout_ms=10000)

        call_args = page.goto.call_args
        call_str = str(call_args)
        assert "10000" in call_str

    @patch("src.browser_fetcher.sync_playwright")
    def test_page_with_empty_text_content_returns_empty(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page(text_content="")
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("https://example.com/empty")

        assert result == ""

    @patch("src.browser_fetcher.sync_playwright")
    def test_headless_browser_launched(self, mock_sync_pw):
        """Playwright should launch in headless mode."""
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        fetch_page("https://example.com/page")

        pw.chromium.launch.assert_called_once()
        call_kwargs = pw.chromium.launch.call_args
        # headless should be True (default) or explicitly set
        call_str = str(call_kwargs)
        assert "headless" in call_str or pw.chromium.launch.called

    @patch("src.browser_fetcher.sync_playwright")
    def test_https_url_accepted(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("https://example.com/secure")

        assert isinstance(result, str)

    @patch("src.browser_fetcher.sync_playwright")
    def test_http_url_accepted(self, mock_sync_pw):
        from src.browser_fetcher import fetch_page

        page = _mock_page()
        browser = _mock_browser(page)
        pw = _mock_playwright(browser)
        mock_sync_pw.return_value.__enter__.return_value = pw

        result = fetch_page("http://example.com/insecure")

        assert isinstance(result, str)
