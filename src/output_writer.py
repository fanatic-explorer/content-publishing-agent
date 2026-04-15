"""Output file I/O and directory structure for the Content Publishing Pipeline Agent.

This module is responsible for generating URL-friendly slugs and writing all
pipeline output files (draft, SEO data, social content, enrichment notes, raw
notes, and pipeline logs) to a structured output directory.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_slug(destination: str, post_type: str) -> str:
    """Create a URL-friendly slug from a destination and post type, appended with the current year-month.

    Args:
        destination: The travel destination name (e.g. "New Zealand", "Jordan").
        post_type: The type of post (e.g. "things-to-do", "best hotels").

    Returns:
        A lowercase, hyphen-separated slug with a YYYY-MM date suffix,
        e.g. "new-zealand-things-to-do-2026-03".
    """
    year_month = datetime.now().strftime("%Y-%m")
    combined = f"{destination}-{post_type}"
    slug = combined.lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    slug = f"{slug}-{year_month}"
    logger.debug(
        f"Generated slug '{slug}' from destination='{destination}', post_type='{post_type}'"
    )
    return slug


def _write_text_file(path: Path, content: str) -> None:
    """Write a string to a file, overwriting any existing content.

    Args:
        path: The file path to write to.
        content: The text content to write.
    """
    path.write_text(content, encoding="utf-8")
    logger.debug(f"Wrote text file: {path}")


def _write_json_file(path: Path, data: dict) -> None:
    """Serialize a dict to a pretty-printed JSON file with UTF-8 encoding.

    Args:
        path: The file path to write to.
        data: The dictionary to serialize.
    """
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    logger.debug(f"Wrote JSON file: {path}")


def write_outputs(
    output_dir: str,
    slug: str,
    draft: str,
    seo: dict,
    social_promotion: dict,
    social_ongoing: dict,
    enrichment: str,
    raw_notes: str,
    pipeline_log: dict,
) -> str:
    """Create the output directory and write all 7 pipeline output files.

    The files are written inside ``<output_dir>/<slug>/``:

    - ``draft.md`` — the article draft
    - ``seo.json`` — SEO research data
    - ``social_promotion.json`` — launch-day social-media copy
    - ``social_ongoing.json`` — ongoing social-media content ideas
    - ``enrichment.md`` — competitor-analysis and enrichment notes
    - ``raw_notes.md`` — raw research notes
    - ``pipeline_log.json`` — pipeline run metadata

    Args:
        output_dir: Base directory under which the slug sub-directory is created.
        slug: The URL-friendly slug used as the sub-directory name.
        draft: Markdown string for the article draft.
        seo: Dictionary containing SEO research data.
        social_promotion: Dictionary containing launch-day social promotion copy.
        social_ongoing: Dictionary containing ongoing social-media content ideas.
        enrichment: Markdown string with enrichment / competitor-analysis notes.
        raw_notes: Markdown string with raw research notes.
        pipeline_log: Dictionary containing pipeline run metadata.

    Returns:
        The absolute path to the created slug sub-directory as a string.

    Raises:
        OSError: If the directory cannot be created or files cannot be written.
    """
    output_path = Path(output_dir) / slug
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Writing pipeline outputs to: {output_path}")

    _write_text_file(output_path / "draft.md", draft)
    _write_json_file(output_path / "seo.json", seo)
    _write_json_file(output_path / "social_promotion.json", social_promotion)
    _write_json_file(output_path / "social_ongoing.json", social_ongoing)
    _write_text_file(output_path / "enrichment.md", enrichment)
    _write_text_file(output_path / "raw_notes.md", raw_notes)
    _write_json_file(output_path / "pipeline_log.json", pipeline_log)

    logger.info(f"Successfully wrote 7 output files to: {output_path}")
    return str(output_path)


def list_drafts(output_dir: str) -> list[dict]:
    """List all existing draft directories in the output directory.

    Scans for subdirectories containing both ``draft.md`` and
    ``pipeline_log.json``. Reads metadata from the pipeline log.

    Args:
        output_dir: Base output directory to scan.

    Returns:
        A list of dicts sorted by slug, each with keys:
        ``slug``, ``destination``, ``post_type``, ``focus_keyword``, ``path``.
    """
    output_path = Path(output_dir)
    if not output_path.is_dir():
        return []

    drafts: list[dict] = []
    for entry in output_path.iterdir():
        if not entry.is_dir():
            continue
        draft_file = entry / "draft.md"
        log_file = entry / "pipeline_log.json"
        if not draft_file.exists() or not log_file.exists():
            continue
        try:
            log_data = json.loads(log_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Skipping {entry.name}: cannot read pipeline_log.json: {exc}")
            continue
        drafts.append(
            {
                "slug": entry.name,
                "destination": log_data.get("destination", ""),
                "post_type": log_data.get("post_type", ""),
                "focus_keyword": log_data.get("focus_keyword", ""),
                "path": str(entry),
            }
        )

    drafts.sort(key=lambda d: d["slug"])
    logger.debug(f"Found {len(drafts)} draft(s) in {output_dir}")
    return drafts


def save_revision(
    output_dir: str,
    slug: str,
    draft: str,
    enrichment_addition: str,
    pipeline_log: dict,
) -> str:
    """Save a revision to an existing draft directory.

    Overwrites ``draft.md`` and ``pipeline_log.json``, appends to
    ``enrichment.md``. Does NOT touch ``seo.json``, ``social_promotion.json``,
    ``social_ongoing.json``, or ``raw_notes.md``.

    Args:
        output_dir: Base output directory.
        slug: The slug subdirectory name.
        draft: The revised draft content.
        enrichment_addition: New enrichment content to append.
        pipeline_log: Updated pipeline log dict (with revisions array).

    Returns:
        The path to the slug subdirectory as a string.

    Raises:
        FileNotFoundError: If the slug directory does not exist.
    """
    output_path = Path(output_dir) / slug
    if not output_path.is_dir():
        raise FileNotFoundError(f"Draft directory not found: {output_path}")

    logger.info(f"Saving revision to: {output_path}")

    _write_text_file(output_path / "draft.md", draft)

    enrichment_file = output_path / "enrichment.md"
    existing_enrichment = ""
    if enrichment_file.exists():
        existing_enrichment = enrichment_file.read_text(encoding="utf-8")
    _write_text_file(enrichment_file, existing_enrichment + enrichment_addition)

    _write_json_file(output_path / "pipeline_log.json", pipeline_log)

    logger.info(f"Revision saved to: {output_path}")
    return str(output_path)


def save_fact_check(output_dir: str, slug: str, fact_check: dict) -> str:
    """Save a fact-check report to an existing draft directory.

    Writes ``fact_check.json`` without touching any other output files.

    Args:
        output_dir: Base output directory.
        slug: The slug subdirectory name.
        fact_check: Fact-check report dict with claims, statuses, and sources.

    Returns:
        The path to the slug subdirectory as a string.

    Raises:
        FileNotFoundError: If the slug directory does not exist.
    """
    output_path = Path(output_dir) / slug
    if not output_path.is_dir():
        raise FileNotFoundError(f"Draft directory not found: {output_path}")

    _write_json_file(output_path / "fact_check.json", fact_check)
    logger.info(f"Fact-check report saved to: {output_path}")
    return str(output_path)
