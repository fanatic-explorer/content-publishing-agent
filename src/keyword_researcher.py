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
                    f"Keysearch returned non-JSON response for '{keyword}': {exc} — "
                    f"body: {body!r}"
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
