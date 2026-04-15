"""Tests for src/keyword_researcher.py — comprehensive TDD test suite."""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keysearch_response(urls=None, difficulty=42) -> dict:
    """Build a fake Keysearch API response dict."""
    if urls is None:
        urls = [
            {"url": "https://travelawaits.com/best-things-to-do-jordan/", "da": 72, "pa": 50},
            {"url": "https://lonelyplanet.com/articles/jordan-travel-guide", "da": 91, "pa": 60},
            {"url": "https://nomadicmatt.com/travel-guides/jordan/", "da": 65, "pa": 40},
        ]
    return {"difficulty": difficulty, "results": urls}


# ---------------------------------------------------------------------------
# research_keyword
# ---------------------------------------------------------------------------


class TestResearchKeyword:
    @pytest.fixture(autouse=True)
    def set_keysearch_key(self, monkeypatch):
        """Ensure KEYSEARCH_API_KEY is set so tests exercise the Keysearch path."""
        monkeypatch.setenv("KEYSEARCH_API_KEY", "test-key")

    @patch("src.keyword_researcher.requests")
    def test_happy_path_returns_difficulty_and_competitors(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("things to do in jordan")

        assert "keyword" in result
        assert "difficulty" in result
        assert "competitors" in result
        assert result["keyword"] == "things to do in jordan"
        assert result["difficulty"] == 42
        assert len(result["competitors"]) <= 5

    @patch("src.keyword_researcher.requests")
    def test_filters_fanaticexplorer_urls(self, mock_requests):
        from src.keyword_researcher import research_keyword

        urls_with_own = [
            {"url": "https://fanaticexplorer.com/jordan-guide/", "da": 50, "pa": 40},
            {"url": "https://travelawaits.com/jordan/", "da": 72, "pa": 50},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response(urls=urls_with_own)
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("things to do in jordan")
        competitor_urls = [c["url"] for c in result["competitors"]]
        assert all("fanaticexplorer.com" not in url for url in competitor_urls)
        assert any("travelawaits.com" in url for url in competitor_urls)

    @patch("src.keyword_researcher.requests")
    def test_returns_at_most_5_competitors(self, mock_requests):
        from src.keyword_researcher import research_keyword

        many_urls = [{"url": f"https://site{i}.com/page/", "da": 50, "pa": 40} for i in range(10)]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response(urls=many_urls)
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("best hotels jordan")
        assert len(result["competitors"]) <= 5

    @patch("src.keyword_researcher.requests")
    def test_none_and_empty_urls_filtered(self, mock_requests):
        from src.keyword_researcher import research_keyword

        urls_with_empties = [
            {"url": None, "da": 50, "pa": 40},
            {"url": "", "da": 50, "pa": 40},
            {"url": "https://travelawaits.com/page/", "da": 72, "pa": 50},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response(urls=urls_with_empties)
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan travel")
        competitor_urls = [c["url"] for c in result["competitors"]]
        assert None not in competitor_urls
        assert "" not in competitor_urls
        assert "https://travelawaits.com/page/" in competitor_urls

    @patch("src.keyword_researcher.requests")
    def test_duplicate_urls_deduplicated(self, mock_requests):
        from src.keyword_researcher import research_keyword

        dup_urls = [
            {"url": "https://travelawaits.com/page/", "da": 72, "pa": 50},
            {"url": "https://travelawaits.com/page/", "da": 72, "pa": 50},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response(urls=dup_urls)
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan hotels")
        urls = [c["url"] for c in result["competitors"]]
        assert len(urls) == len(set(urls))

    @patch("src.keyword_researcher.requests")
    def test_keysearch_429_returns_null_difficulty(self, mock_requests):
        from requests.exceptions import HTTPError

        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_resp.status_code = 429
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None

    @patch("src.keyword_researcher.requests")
    def test_keysearch_401_returns_null_difficulty(self, mock_requests):
        from requests.exceptions import HTTPError

        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_resp.status_code = 401
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None

    @patch("src.keyword_researcher.requests")
    def test_keysearch_timeout_returns_null_difficulty(self, mock_requests):
        from requests.exceptions import Timeout

        from src.keyword_researcher import research_keyword

        mock_requests.get.side_effect = Timeout("Connection timed out")

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None

    @patch("src.keyword_researcher.requests")
    def test_zero_results_returns_empty_competitors(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"difficulty": 30, "results": []}
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("obscure keyword nobody searches")
        assert result["competitors"] == []

    @patch("src.keyword_researcher.requests")
    def test_missing_api_key_returns_null_difficulty(self, mock_requests, monkeypatch):
        from src.keyword_researcher import research_keyword

        monkeypatch.delenv("KEYSEARCH_API_KEY", raising=False)

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None

    @patch("src.keyword_researcher.requests")
    def test_competitors_have_url_da_pa_keys(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keyword("things to do in jordan")
        for comp in result["competitors"]:
            assert "url" in comp
            assert "da" in comp
            assert "pa" in comp

    @patch("src.keyword_researcher.requests")
    def test_calls_correct_api_url(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        research_keyword("things to do in jordan")

        call_args = mock_requests.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert url == "https://www.keysearch.co/api", (
            f"Expected URL 'https://www.keysearch.co/api', got {url!r}. "
            "Keysearch's documented endpoint is /api, not /api/difficulty."
        )

    @patch("src.keyword_researcher.requests")
    def test_uses_difficulty_param_not_keyword(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        research_keyword("jordan travel")

        params = mock_requests.get.call_args.kwargs["params"]
        assert params.get("difficulty") == "jordan travel", (
            "Keysearch API expects the keyword under the 'difficulty' query param, "
            "not 'keyword' — see https://www.keysearch.co/api/documentation"
        )
        assert "keyword" not in params, (
            "The 'keyword' param is not a valid Keysearch parameter and will be ignored."
        )

    @patch("src.keyword_researcher.requests")
    def test_sends_cr_country_param(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        research_keyword("jordan travel")

        params = mock_requests.get.call_args.kwargs["params"]
        assert params.get("cr") == "us"

    @patch("src.keyword_researcher.requests")
    def test_non_json_response_returns_null_difficulty(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_resp.text = "Some unexpected plain text body from the API"
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None
        assert result["competitors"] == []
        assert result["keyword"] == "jordan travel"

    @patch("src.keyword_researcher.requests")
    def test_account_not_searched_message_logged_as_warning(self, mock_requests, caplog):
        import logging

        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_resp.text = (
            "The keyword and location combination did not return results from "
            "your account. The difficulty API is meant to access keywords already "
            "searched within your account."
        )
        mock_requests.get.return_value = mock_resp

        with caplog.at_level(logging.WARNING, logger="src.keyword_researcher"):
            result = research_keyword("things to do in jaipur")

        assert result["difficulty"] is None
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "Expected a WARNING log entry for 'not searched in account'"
        combined = " ".join(r.getMessage() for r in warnings).lower()
        assert "things to do in jaipur" in combined
        assert "keysearch" in combined or "dashboard" in combined


# ---------------------------------------------------------------------------
# research_keywords_batch
# ---------------------------------------------------------------------------


class TestResearchKeywordsBatch:
    @pytest.fixture(autouse=True)
    def set_keysearch_key(self, monkeypatch):
        """Ensure KEYSEARCH_API_KEY is set."""
        monkeypatch.setenv("KEYSEARCH_API_KEY", "test-key")

    @patch("src.keyword_researcher.time")
    @patch("src.keyword_researcher.requests")
    def test_batch_returns_list_of_results(self, mock_requests, mock_time):
        from src.keyword_researcher import research_keywords_batch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        keywords = ["jordan travel", "best hotels jordan"]
        result = research_keywords_batch(keywords)
        assert isinstance(result, list)
        assert len(result) == 2

    @patch("src.keyword_researcher.time")
    @patch("src.keyword_researcher.requests")
    def test_batch_calls_sleep_between_keywords(self, mock_requests, mock_time):
        from src.keyword_researcher import research_keywords_batch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        keywords = ["keyword1", "keyword2", "keyword3"]
        research_keywords_batch(keywords)
        # Should sleep between calls (at least n-1 times for n keywords)
        assert mock_time.sleep.call_count >= 2
        mock_time.sleep.assert_called_with(1)

    @patch("src.keyword_researcher.time")
    @patch("src.keyword_researcher.requests")
    def test_batch_empty_list_returns_empty(self, mock_requests, mock_time):
        from src.keyword_researcher import research_keywords_batch

        result = research_keywords_batch([])
        assert result == []
        mock_requests.get.assert_not_called()

    @patch("src.keyword_researcher.time")
    @patch("src.keyword_researcher.requests")
    def test_batch_single_keyword_no_sleep(self, mock_requests, mock_time):
        from src.keyword_researcher import research_keywords_batch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        result = research_keywords_batch(["single keyword"])
        assert len(result) == 1
        # No sleep needed for a single keyword (no gap between calls)
        assert mock_time.sleep.call_count == 0

    @patch("src.keyword_researcher.time")
    @patch("src.keyword_researcher.requests")
    def test_batch_preserves_keyword_order(self, mock_requests, mock_time):
        from src.keyword_researcher import research_keywords_batch

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        keywords = ["alpha keyword", "beta keyword", "gamma keyword"]
        result = research_keywords_batch(keywords)
        assert [r["keyword"] for r in result] == keywords
