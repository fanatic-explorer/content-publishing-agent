"""keyword_researcher.py — Keyword difficulty and competitor research via Keysearch API.

Provides functions to look up keyword difficulty scores and competing URLs
for given keyword strings. Gracefully degrades to null difficulty when the
API key is missing or the API returns an error.

Keysearch API notes (discovered by live probing — docs are incomplete):
- Base URL: https://www.keysearch.co/api
- Two relevant endpoints, distinguished by query param:
  - /api?key=<K>&difficulty=<keyword>&cr=<country>  → single keyword lookup
  - /api?key=<K>&list=<name>                         → bulk fetch of saved list
- The `cr` (country) parameter is quirky:
  - `cr=all`         → global (worldwide) search data  ← our default
  - `cr=us` or empty → United States data
  - `cr=global`, `worldwide`, etc. → NOT valid (returns cache miss)
- The difficulty endpoint is a READ-through cache on top of the Keysearch
  web UI. It only returns data for (keyword, location) pairs that have
  been explicitly searched in the Keyword Research → Quick Difficulty
  tool first. For new keywords, you get a text body:
  "The keyword and location combination did not return results from your
  account. The difficulty API is meant to access keywords already
  searched within your account."
- The saved-list endpoint (/api?list=<name>) bypasses this cache-seeding
  issue and is the recommended path for pipeline use — see research_list().
- Real response field names differ from a naive expectation:
  - Difficulty score is under `score` (as a string like "36"), not `difficulty`
  - SERP competitors are under `json_result` as a **JSON-encoded string**
    that must be parsed again before use
  - Each SERP item has `url` (lowercase) but `DA`, `PA` (uppercase), all strings
"""

import json
import logging
import os
import time

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError, Timeout

load_dotenv()

logger = logging.getLogger(__name__)

KEYSEARCH_API_URL = "https://www.keysearch.co/api"
# 'all' = global (worldwide) search data. 'us' = United States. See docstring above
# for the full list of valid values. Override via KEYSEARCH_COUNTRY env var.
KEYSEARCH_COUNTRY = os.getenv("KEYSEARCH_COUNTRY", "all")
OWN_DOMAIN = "fanaticexplorer.com"


def _to_int(value: object) -> int | None:
    """Cast a Keysearch string value to int, returning None on failure."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def _to_float(value: object) -> float | None:
    """Cast a Keysearch string value to float, returning None on failure."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None


def _filter_competitors(raw_results: list[dict]) -> list[dict]:
    """Filter, deduplicate, and limit Keysearch SERP competitor dicts to 5.

    Keysearch returns SERP items inside the `json_result` field with keys
    `url` (lowercase), `DA`, and `PA` (uppercase) — all as strings. This
    function normalizes them to our internal shape with lowercase `da`/`pa`
    as integers.

    Args:
        raw_results: List of SERP item dicts as parsed from the Keysearch
            `json_result` field. Expected keys: `url`, `DA`, `PA`.

    Returns:
        Up to 5 unique competitor dicts, each with lowercase 'url', 'da'
        (int or None), and 'pa' (int or None). Entries with empty URLs or
        URLs from OWN_DOMAIN are excluded.
    """
    seen: set[str] = set()
    result: list[dict] = []
    for item in raw_results:
        url = item.get("url")
        if not url:
            continue
        if OWN_DOMAIN in url:
            continue
        if url in seen:
            continue
        seen.add(url)
        result.append(
            {
                "url": url,
                "da": _to_int(item.get("DA")),
                "pa": _to_int(item.get("PA")),
            }
        )
        if len(result) >= 5:
            break
    return result


def research_keyword(keyword: str) -> dict:
    """Research difficulty and competitor URLs for a single keyword via Keysearch.

    Calls the Keysearch difficulty endpoint for one (keyword, country) pair
    and normalizes the response. Returns null difficulty and an empty
    competitors list when the API key is absent, the API call fails, or the
    keyword has not been pre-seeded in the Keysearch web dashboard (see the
    module docstring for details on the cache-seeding requirement).

    For bulk/pipeline use, prefer research_list() — it reads from a
    persisted saved list and sidesteps the per-keyword cache-miss issue.

    Args:
        keyword: The keyword string to research. Uses KEYSEARCH_COUNTRY
            (default 'all' = global) for the location.

    Returns:
        Dict with:
            - 'keyword': the original keyword string
            - 'difficulty': int 0-100 Keysearch score, or None on failure
            - 'competitors': list of dicts with 'url', 'da', 'pa' keys
              (up to 5 entries, fanaticexplorer.com excluded, deduplicated)

    Raises:
        No exceptions are raised; all errors are caught and logged.
    """
    null_result: dict = {"keyword": keyword, "difficulty": None, "competitors": []}

    api_key = os.getenv("KEYSEARCH_API_KEY")
    if not api_key:
        logger.warning("KEYSEARCH_API_KEY not set — skipping Keysearch lookup.")
        return null_result

    try:
        response = requests.get(
            KEYSEARCH_API_URL,
            params={"key": api_key, "difficulty": keyword, "cr": KEYSEARCH_COUNTRY},
            timeout=15,
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            body = (response.text or "")[:300]
            # The difficulty endpoint returns cache-miss errors as plain text
            # (not JSON-encoded), so response.json() raises. Detect the known
            # "already searched" message and log a friendly warning.
            if "already searched within your account" in body:
                logger.warning(
                    f"Keysearch has no cached data for '{keyword}' (country={KEYSEARCH_COUNTRY}). "
                    f"The difficulty API only returns keywords already searched in your "
                    f"Keysearch dashboard — log in to keysearch.co, run this keyword via "
                    f"Keyword Research → Quick Difficulty with location='Global (All Locations)', "
                    f"then retry. Or use research_list() with a pre-saved list."
                )
            else:
                logger.error(
                    f"Keysearch returned non-JSON response for '{keyword}': {exc} — body: {body!r}"
                )
            return null_result

        # Defensive: the difficulty endpoint shouldn't return a string after a
        # successful json() parse, but handle it for forward compatibility.
        if isinstance(data, str):
            logger.warning(
                f"Keysearch returned unexpected string response for '{keyword}': {data!r}"
            )
            return null_result

        if not isinstance(data, dict):
            logger.error(
                f"Unexpected Keysearch response type for '{keyword}': "
                f"{type(data).__name__} — expected dict."
            )
            return null_result

        difficulty = _to_int(data.get("score"))

        # SERP competitors live under `json_result` as a nested JSON string
        raw_serp_str = data.get("json_result") or "[]"
        try:
            raw_results = json.loads(raw_serp_str) if isinstance(raw_serp_str, str) else []
        except json.JSONDecodeError as exc:
            logger.error(
                f"Failed to parse Keysearch json_result for '{keyword}': {exc} — "
                f"body: {raw_serp_str[:200]!r}"
            )
            raw_results = []

        if not isinstance(raw_results, list):
            raw_results = []

        competitors = _filter_competitors(raw_results)
        return {"keyword": keyword, "difficulty": difficulty, "competitors": competitors}

    except HTTPError as exc:
        logger.error(f"Keysearch HTTP error for '{keyword}': {exc}")
        return null_result

    except Timeout as exc:
        logger.error(f"Keysearch request timed out for '{keyword}': {exc}")
        return null_result


def research_keywords_batch(keywords: list[str]) -> list[dict]:
    """Research difficulty and competitors for a list of keywords.

    Calls research_keyword for each keyword in order, sleeping 1 second
    between successive calls to respect Keysearch rate limits.

    Args:
        keywords: List of keyword strings to research.

    Returns:
        List of result dicts in the same order as the input keywords. Each
        dict has the same shape as the return value of research_keyword.
    """
    results: list[dict] = []
    for index, keyword in enumerate(keywords):
        results.append(research_keyword(keyword))
        if index < len(keywords) - 1:
            time.sleep(1)
    return results


def _normalize_list_item(item: dict) -> dict | None:
    """Normalize a raw Keysearch list item into our standard shape.

    Keysearch returns all values as strings (e.g. "39", "2900", "0.18").
    This function casts them to int/float where possible and returns None
    for items missing a keyword field.

    Args:
        item: Raw dict from the Keysearch /api?list= response.

    Returns:
        Normalized dict with 'keyword', 'difficulty', 'volume', 'cpc',
        'competition', and 'competitors' keys. Returns None if the item
        has no usable keyword field.
    """
    keyword = item.get("keyword")
    if not keyword:
        return None
    return {
        "keyword": keyword,
        "difficulty": _to_int(item.get("score")),
        "volume": _to_int(item.get("volume")),
        "cpc": _to_float(item.get("cpc")),
        "competition": _to_float(item.get("competition")),
        "competitors": [],
    }


def research_list(list_name: str) -> list[dict]:
    """Fetch all keywords from a saved Keysearch list with their metrics.

    Unlike research_keyword/research_keywords_batch — which hit the
    difficulty endpoint for individual keywords and suffer from Keysearch's
    cache-miss problem for keywords not previously searched in the web UI —
    this function reads from a persisted server-side list. One API call
    returns every keyword in the list with difficulty, volume, CPC, and
    competition data.

    Setup: In the Keysearch web UI, go to Keyword Research → Quick
    Difficulty, run your candidate keywords, tick them all, and click
    Save Keywords to create a named list. Pass the same list name here.

    Note: Keysearch strips non-alphanumeric characters from list names on
    the server side. A UI list named "my_test_list" is addressable as
    "mytestlist" via the API. If a list is "not found", the most common
    cause is underscores/spaces in the name.

    Args:
        list_name: Name of the saved list. Should be alphanumeric only —
            see note above about server-side name transformations.

    Returns:
        List of dicts, each with keys:
            - 'keyword': the keyword string
            - 'difficulty': int 0-100 (Keysearch score), or None if unparseable
            - 'volume': int monthly search volume, or None if unparseable
            - 'cpc': float cost-per-click in USD, or None if unparseable
            - 'competition': float 0-1 advertiser competition, or None
            - 'competitors': empty list (list endpoint does not return SERP
              competitor URLs — use research_keyword() for that data)
        Duplicate keywords are deduplicated, keeping the entry with the
        highest volume. First-seen order is preserved.
        Returns an empty list when the API key is missing, the list is not
        found, or the API call fails.

    Raises:
        No exceptions are raised; all errors are caught and logged.
    """
    null_result: list[dict] = []

    api_key = os.getenv("KEYSEARCH_API_KEY")
    if not api_key:
        logger.warning("KEYSEARCH_API_KEY not set — skipping Keysearch list fetch.")
        return null_result

    try:
        response = requests.get(
            KEYSEARCH_API_URL,
            params={"key": api_key, "list": list_name},
            timeout=15,
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            body = (response.text or "")[:300]
            logger.error(
                f"Keysearch returned non-JSON response for list '{list_name}': "
                f"{exc} — body: {body!r}"
            )
            return null_result

        if isinstance(data, str):
            logger.warning(
                f"Keysearch list '{list_name}' not found (server response: {data!r}). "
                f"Keysearch strips non-alphanumeric characters from list names — "
                f"a UI list named 'my_list' is addressable as 'mylist' via the API. "
                f"Verify the exact name in your Keysearch dashboard."
            )
            return null_result

        if not isinstance(data, list):
            logger.error(
                f"Unexpected Keysearch list response type for '{list_name}': "
                f"{type(data).__name__} — expected list. Body: {data!r}"
            )
            return null_result

        by_keyword: dict[str, dict] = {}
        for raw in data:
            normalized = _normalize_list_item(raw)
            if normalized is None:
                continue
            kw = normalized["keyword"]
            existing = by_keyword.get(kw)
            if existing is None:
                by_keyword[kw] = normalized
            else:
                existing_volume = existing["volume"] or 0
                new_volume = normalized["volume"] or 0
                if new_volume > existing_volume:
                    by_keyword[kw] = normalized

        return list(by_keyword.values())

    except HTTPError as exc:
        logger.error(f"Keysearch HTTP error for list '{list_name}': {exc}")
        return null_result

    except Timeout as exc:
        logger.error(f"Keysearch request timed out for list '{list_name}': {exc}")
        return null_result
