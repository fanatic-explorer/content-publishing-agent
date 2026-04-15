"""Tests for src/keyword_researcher.py — comprehensive TDD test suite."""

import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _keysearch_response(urls=None, difficulty=42) -> dict:
    """Build a fake Keysearch difficulty-endpoint response dict.

    Matches the real API shape captured from live probing: top-level dict
    with `score` (string), `keyword`, `location`, `cpc`, `ppc`, `volume`,
    and `json_result` (a JSON-encoded string containing SERP items with
    uppercase DA/PA keys).
    """
    if urls is None:
        urls = [
            {"url": "https://travelawaits.com/best-things-to-do-jordan/", "DA": "72", "PA": "50"},
            {
                "url": "https://lonelyplanet.com/articles/jordan-travel-guide",
                "DA": "91",
                "PA": "60",
            },
            {"url": "https://nomadicmatt.com/travel-guides/jordan/", "DA": "65", "PA": "40"},
        ]
    return {
        "id": "308484514",
        "keyword": "test keyword",
        "location": "all",
        "cpc": "0.18",
        "ppc": "0.78",
        "volume": "260",
        "score": str(difficulty),
        "json_result": json.dumps(urls),
    }


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
            {"url": "https://fanaticexplorer.com/jordan-guide/", "DA": "50", "PA": "40"},
            {"url": "https://travelawaits.com/jordan/", "DA": "72", "PA": "50"},
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

        many_urls = [
            {"url": f"https://site{i}.com/page/", "DA": "50", "PA": "40"} for i in range(10)
        ]
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
            {"url": None, "DA": "50", "PA": "40"},
            {"url": "", "DA": "50", "PA": "40"},
            {"url": "https://travelawaits.com/page/", "DA": "72", "PA": "50"},
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
            {"url": "https://travelawaits.com/page/", "DA": "72", "PA": "50"},
            {"url": "https://travelawaits.com/page/", "DA": "72", "PA": "50"},
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
        mock_resp.json.return_value = _keysearch_response(urls=[], difficulty=30)
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
    def test_competitors_have_url_da_pa_keys_as_ints(self, mock_requests):
        """DA/PA come from the API as uppercase strings ('72') and should be
        normalized to lowercase int fields on our internal shape."""
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
            # DA/PA should be parsed from the API's string values into ints
            assert isinstance(comp["da"], int)
            assert isinstance(comp["pa"], int)
        # Spot-check the specific values match the helper fixture
        first = result["competitors"][0]
        assert first["da"] == 72
        assert first["pa"] == 50

    @patch("src.keyword_researcher.requests")
    def test_parses_json_result_string_field(self, mock_requests):
        """The Keysearch difficulty endpoint returns SERP data under
        `json_result` as a nested JSON STRING (not a list). Verify parsing."""
        from src.keyword_researcher import research_keyword

        # Explicit response matching the real Keysearch shape including the
        # nested JSON-string field
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "id": "308484514",
            "keyword": "jaipur travel guide",
            "location": "all",
            "cpc": "0.18",
            "ppc": "0.78",
            "volume": "260",
            "score": "36",
            "json_result": (
                '[{"url":"https://thirdeyetraveller.com/jaipur/","PA":"36","DA":"43"},'
                '{"url":"https://travelandleisure.com/jaipur","PA":"54","DA":"89"}]'
            ),
        }
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jaipur travel guide")
        assert result["difficulty"] == 36
        assert len(result["competitors"]) == 2
        assert result["competitors"][0]["url"] == "https://thirdeyetraveller.com/jaipur/"
        assert result["competitors"][0]["da"] == 43
        assert result["competitors"][0]["pa"] == 36
        assert result["competitors"][1]["da"] == 89

    @patch("src.keyword_researcher.requests")
    def test_malformed_json_result_string_returns_empty_competitors(self, mock_requests):
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "id": "1",
            "keyword": "test",
            "score": "42",
            "json_result": "not valid json at all }}[{",
        }
        mock_requests.get.return_value = mock_resp

        result = research_keyword("test")
        assert result["difficulty"] == 42
        assert result["competitors"] == []  # malformed json_result degrades gracefully

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
    def test_sends_cr_country_param_defaults_to_all(self, mock_requests):
        """Default KEYSEARCH_COUNTRY is 'all' (global)."""
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _keysearch_response()
        mock_resp.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_resp

        research_keyword("jordan travel")

        params = mock_requests.get.call_args.kwargs["params"]
        assert params.get("cr") == "all"

    @patch("src.keyword_researcher.requests")
    def test_non_json_response_returns_null_difficulty(self, mock_requests):
        """True non-JSON body (e.g. HTML error page) should not crash."""
        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_resp.text = "<html>unexpected error page</html>"
        mock_requests.get.return_value = mock_resp

        result = research_keyword("jordan travel")
        assert result["difficulty"] is None
        assert result["competitors"] == []
        assert result["keyword"] == "jordan travel"

    @patch("src.keyword_researcher.requests")
    def test_account_not_searched_returns_null_and_warns(self, mock_requests, caplog):
        """Real Keysearch cache-miss for the difficulty endpoint: HTTP 200
        with a *plain text* body (not JSON-encoded), so response.json()
        raises ValueError and we detect the error message from response.text.
        """
        import logging

        from src.keyword_researcher import research_keyword

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        # Real difficulty-endpoint cache-miss behavior: body is plain text
        # (not valid JSON), json() raises ValueError, and we check response.text.
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
        assert result["competitors"] == []
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


# ---------------------------------------------------------------------------
# research_list — bulk fetch from a saved Keysearch list
# ---------------------------------------------------------------------------


def _list_response(items=None):
    """Build a fake Keysearch /api?list= response.

    Matches the real response shape captured from live API: a top-level JSON
    array of dicts with string values for all numeric fields (keyword,
    volume, cpc, competition, score).
    """
    if items is None:
        items = [
            {
                "keyword": "jaipur travel guide",
                "volume": "260",
                "cpc": "0.18",
                "competition": "0.78",
                "score": "36",
            },
            {
                "keyword": "best things to do in jaipur",
                "volume": "590",
                "cpc": "0.11",
                "competition": "0.41",
                "score": "40",
            },
            {
                "keyword": "jaipur itinerary",
                "volume": "2900",
                "cpc": "0.13",
                "competition": "0.35",
                "score": "27",
            },
        ]
    return items


class TestResearchList:
    @pytest.fixture(autouse=True)
    def set_keysearch_key(self, monkeypatch):
        """Ensure KEYSEARCH_API_KEY is set so tests exercise the real path."""
        monkeypatch.setenv("KEYSEARCH_API_KEY", "test-key")

    @patch("src.keyword_researcher.requests")
    def test_happy_path_returns_normalized_keywords(self, mock_requests):
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = _list_response()
        mock_requests.get.return_value = mock_resp

        result = research_list("jaipurtestlist")

        assert isinstance(result, list)
        assert len(result) == 3
        first = result[0]
        assert first["keyword"] == "jaipur travel guide"
        assert first["difficulty"] == 36
        assert first["volume"] == 260
        assert first["cpc"] == 0.18
        assert first["competition"] == 0.78
        # list endpoint does not return SERP competitors — empty for API consistency
        assert first["competitors"] == []

    @patch("src.keyword_researcher.requests")
    def test_calls_correct_endpoint_with_list_param(self, mock_requests):
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = []
        mock_requests.get.return_value = mock_resp

        research_list("jaipurtestlist")

        call_args = mock_requests.get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url")
        assert url == "https://www.keysearch.co/api"
        params = call_args.kwargs["params"]
        assert params.get("list") == "jaipurtestlist"
        assert params.get("key") == "test-key"
        # cr/country is NOT passed for list endpoint — list is stored server-side
        assert "cr" not in params
        # difficulty= is NOT passed either
        assert "difficulty" not in params

    @patch("src.keyword_researcher.requests")
    def test_deduplicates_keywords_keeping_max_volume(self, mock_requests):
        """Real Keysearch behavior: same keyword can appear multiple times."""
        from src.keyword_researcher import research_list

        items = [
            {
                "keyword": "jaipur travel guide",
                "volume": "10",
                "cpc": "0",
                "competition": "0",
                "score": "39",
            },
            {
                "keyword": "jaipur travel guide",
                "volume": "260",
                "cpc": "0.18",
                "competition": "0.78",
                "score": "36",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = items
        mock_requests.get.return_value = mock_resp

        result = research_list("jaipurtestlist")

        assert len(result) == 1
        assert result[0]["keyword"] == "jaipur travel guide"
        assert result[0]["volume"] == 260  # kept the higher-volume entry
        assert result[0]["difficulty"] == 36
        assert result[0]["cpc"] == 0.18

    @patch("src.keyword_researcher.requests")
    def test_preserves_first_seen_order_across_dedup(self, mock_requests):
        from src.keyword_researcher import research_list

        items = [
            {"keyword": "alpha", "volume": "100", "cpc": "0", "competition": "0", "score": "10"},
            {"keyword": "beta", "volume": "50", "cpc": "0", "competition": "0", "score": "20"},
            {"keyword": "alpha", "volume": "200", "cpc": "0", "competition": "0", "score": "15"},
            {"keyword": "gamma", "volume": "75", "cpc": "0", "competition": "0", "score": "30"},
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = items
        mock_requests.get.return_value = mock_resp

        result = research_list("mixed")
        keywords_in_order = [r["keyword"] for r in result]
        assert keywords_in_order == ["alpha", "beta", "gamma"]
        # alpha's volume is the higher of the two duplicates (200)
        assert result[0]["volume"] == 200

    @patch("src.keyword_researcher.requests")
    def test_list_not_found_returns_empty_list(self, mock_requests):
        """Real Keysearch error: JSON-encoded string body."""
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = "This list not Found Please search other list"
        mock_requests.get.return_value = mock_resp

        result = research_list("nonexistent_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_list_not_found_logs_warning_with_name_hint(self, mock_requests, caplog):
        import logging

        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = "This list not Found Please search other list"
        mock_requests.get.return_value = mock_resp

        with caplog.at_level(logging.WARNING, logger="src.keyword_researcher"):
            research_list("my_test_list")

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings
        combined = " ".join(r.getMessage() for r in warnings).lower()
        assert "my_test_list" in combined
        # Hint should mention the alphanumeric-only transformation
        assert "alphanumeric" in combined or "non-alphanumeric" in combined or "strip" in combined

    @patch("src.keyword_researcher.requests")
    def test_empty_list_returns_empty(self, mock_requests):
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = []
        mock_requests.get.return_value = mock_resp

        result = research_list("empty_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_missing_api_key_returns_empty(self, mock_requests, monkeypatch):
        from src.keyword_researcher import research_list

        monkeypatch.delenv("KEYSEARCH_API_KEY", raising=False)
        result = research_list("any_list")
        assert result == []
        mock_requests.get.assert_not_called()

    @patch("src.keyword_researcher.requests")
    def test_http_401_returns_empty(self, mock_requests):
        from requests.exceptions import HTTPError

        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_requests.get.return_value = mock_resp

        result = research_list("any_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_timeout_returns_empty(self, mock_requests):
        from requests.exceptions import Timeout

        from src.keyword_researcher import research_list

        mock_requests.get.side_effect = Timeout("Connection timed out")

        result = research_list("any_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_non_json_response_returns_empty(self, mock_requests):
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
        mock_resp.text = "<html>unexpected error page</html>"
        mock_requests.get.return_value = mock_resp

        result = research_list("any_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_unexpected_dict_response_returns_empty(self, mock_requests):
        """Defensive: if Keysearch ever changes to a dict wrapper, don't crash."""
        from src.keyword_researcher import research_list

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"unexpected": "wrapper"}
        mock_requests.get.return_value = mock_resp

        result = research_list("any_list")
        assert result == []

    @patch("src.keyword_researcher.requests")
    def test_malformed_numeric_values_normalized_to_none(self, mock_requests):
        """Keysearch can return empty strings or non-numeric values."""
        from src.keyword_researcher import research_list

        items = [
            {
                "keyword": "edge case kw",
                "volume": "",
                "cpc": "N/A",
                "competition": "",
                "score": "",
            },
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = items
        mock_requests.get.return_value = mock_resp

        result = research_list("edge")
        assert len(result) == 1
        assert result[0]["keyword"] == "edge case kw"
        assert result[0]["difficulty"] is None
        assert result[0]["volume"] is None
        assert result[0]["cpc"] is None
        assert result[0]["competition"] is None

    @patch("src.keyword_researcher.requests")
    def test_item_without_keyword_field_skipped(self, mock_requests):
        from src.keyword_researcher import research_list

        items = [
            {"keyword": "valid", "volume": "100", "cpc": "1", "competition": "0.5", "score": "30"},
            {"volume": "50"},  # missing keyword — should be skipped
            {"keyword": "", "volume": "75"},  # empty keyword — should be skipped
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = items
        mock_requests.get.return_value = mock_resp

        result = research_list("mixed")
        assert len(result) == 1
        assert result[0]["keyword"] == "valid"
