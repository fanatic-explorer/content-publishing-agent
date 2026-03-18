"""browser_fetcher.py — Fetch page text content using a headless Playwright browser.

Uses Playwright's synchronous API with headless Chromium to navigate to a URL
and extract the visible text content of the page.
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def fetch_page(url: str, timeout_ms: int = 30000) -> str:
    """Fetch the text content of a web page using a headless Chromium browser.

    Validates the URL, launches a headless Chromium browser, navigates to the
    URL, and returns the text content. Always closes the browser, even on error.
    Returns an empty string for 404 responses or pages with no text content.

    Args:
        url: The URL to fetch. Must include a scheme (http:// or https://).
        timeout_ms: Navigation timeout in milliseconds. Defaults to 30000.

    Returns:
        The text content of the page, or an empty string on 404 or empty pages.

    Raises:
        ValueError: If the URL is missing a scheme or is otherwise invalid.
        TimeoutError: If the page navigation times out.
        ConnectionError: If the connection is refused or the host is unreachable.
    """
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL — must include http:// or https:// scheme: {url!r}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            response = page.goto(url, timeout=timeout_ms)

            if response is not None and response.status == 404:
                logger.warning("Page returned 404 for URL: %s", url)
                return ""

            text = page.text_content("body") or ""
            return text
        finally:
            browser.close()
