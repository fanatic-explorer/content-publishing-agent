"""keyword_researcher.py — Keyword difficulty and competitor research via Keysearch API.

Provides functions to look up keyword difficulty scores and competing URLs
for given keyword strings. Gracefully degrades to null difficulty when the
API key is missing or the API returns an error.
"""

import logging
import os
import time

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError, Timeout

load_dotenv()

logger = logging.getLogger(__name__)

KEYSEARCH_API_URL = "https://www.keysearch.co/api"
KEYSEARCH_COUNTRY = os.getenv("KEYSEARCH_COUNTRY", "us")
OWN_DOMAIN = "fanaticexplorer.com"


def _filter_competitors(raw_results: list[dict]) -> list[dict]:
    """Filter, deduplicate, and limit competitor result dicts to 5.

    Removes entries with None/empty URLs, results from OWN_DOMAIN, and
    duplicates. Preserves da/pa fields from the original result dicts.

    Args:
        raw_results: List of dicts with 'url', 'da', and 'pa' keys as
            returned by the Keysearch API.

    Returns:
        Up to 5 unique competitor dicts, each with 'url', 'da', and 'pa'.
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
        result.append({"url": url, "da": item.get("da"), "pa": item.get("pa")})
        if len(result) >= 5:
            break
    return result


def research_keyword(keyword: str) -> dict:
    """Research difficulty and competitor URLs for a keyword via Keysearch.

    Calls the Keysearch API to obtain the keyword difficulty score and a list
    of competing URLs for the given keyword. Returns null difficulty and an
    empty competitors list when the API key is absent or the API call fails.

    Args:
        keyword: The keyword string to research.

    Returns:
        Dict with:
            - 'keyword': the original keyword string.
            - 'difficulty': int difficulty score from Keysearch, or None on failure.
            - 'competitors': list of dicts with 'url', 'da', and 'pa' keys
              (up to 5 entries, fanaticexplorer.com excluded, deduplicated).

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
            if "already searched within your account" in body:
                logger.warning(
                    f"Keysearch has no cached data for '{keyword}'. The Keysearch "
                    f"difficulty API only returns keywords already searched in your "
                    f"dashboard — log in to keysearch.co, search '{keyword}' once, "
                    f"then retry."
                )
            else:
                logger.error(
                    f"Keysearch returned non-JSON response for '{keyword}': {exc} — body: {body!r}"
                )
            return null_result

        difficulty = data.get("difficulty")
        raw_results = data.get("results", [])

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
