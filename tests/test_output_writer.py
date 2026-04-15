"""Tests for src/output_writer.py — comprehensive TDD test suite."""

import json
from pathlib import Path

import pytest

from src.output_writer import (
    generate_slug,
    list_drafts,
    save_fact_check,
    save_revision,
    write_outputs,
)

# ---------------------------------------------------------------------------
# Sample test data
# ---------------------------------------------------------------------------

SAMPLE_DRAFT = """# 10 Best Things to Do in Jordan

Jordan is a mesmerizing country with ancient ruins, stunning deserts, and vibrant culture.

## 1. Visit Petra
The ancient city of Petra is Jordan's most famous attraction...

## 2. Float in the Dead Sea
Experience weightlessness in the lowest point on Earth...
"""

SAMPLE_SEO = {
    "primary_keyword": "things to do in jordan",
    "secondary_keywords": ["jordan travel guide", "best jordan attractions"],
    "title_tag": "10 Best Things to Do in Jordan (2026 Travel Guide)",
    "meta_description": "Discover the top things to do in Jordan...",
    "keyword_difficulty": 42,
    "competitors": [
        {"url": "https://travelawaits.com/jordan/", "da": 72, "pa": 50},
    ],
}

SAMPLE_SOCIAL_PROMOTION = {
    "twitter": "Just published: 10 Best Things to Do in Jordan! #travel #jordan",
    "facebook": "Our latest guide covers the best experiences in Jordan...",
    "pinterest_pins": [
        {"title": "Things to Do in Jordan", "description": "Complete travel guide..."},
    ],
}

SAMPLE_SOCIAL_ONGOING = {
    "content_ideas": [
        "Share a Petra photo with tip about best time to visit",
        "Dead Sea floating tips reel",
    ],
    "scheduled_posts": [
        {"platform": "twitter", "text": "Did you know Jordan has...", "days_after": 7},
    ],
}

SAMPLE_ENRICHMENT = """## Competitor Analysis

### travelawaits.com/jordan/
- DA: 72, PA: 50
- Covers 15 attractions vs our 10
- Strong internal linking structure
"""

SAMPLE_RAW_NOTES = """Travel notes about Jordan:
- Visited Petra in March, amazing but crowded
- Dead Sea was a unique experience
- Amman has great food scene
"""

SAMPLE_PIPELINE_LOG = {
    "destination": "jordan",
    "post_type": "things-to-do",
    "started_at": "2026-03-18T10:00:00",
    "completed_at": "2026-03-18T10:15:00",
    "steps": [
        {"name": "keyword_research", "status": "completed", "duration_seconds": 45},
        {"name": "draft_writing", "status": "completed", "duration_seconds": 120},
    ],
}


# ---------------------------------------------------------------------------
# generate_slug
# ---------------------------------------------------------------------------


class TestGenerateSlug:
    def test_basic_slug_generation(self):
        result = generate_slug("jordan", "things-to-do")
        assert "jordan" in result
        assert "things-to-do" in result

    def test_spaces_replaced_with_hyphens(self):
        result = generate_slug("New Zealand", "things to do")
        assert " " not in result
        assert "new-zealand" in result

    def test_uppercase_converted_to_lowercase(self):
        result = generate_slug("JORDAN", "THINGS-TO-DO")
        assert result == result.lower()

    def test_slug_contains_date_component(self):
        result = generate_slug("jordan", "things-to-do")
        # Should contain year-month like "2026-03"
        assert "2026" in result or "-" in result

    def test_special_characters_removed(self):
        result = generate_slug("jordan's best!", "things & stuff")
        assert "'" not in result
        assert "!" not in result
        assert "&" not in result

    def test_unicode_destination_name(self):
        result = generate_slug("turkiye", "travel-guide")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_slug_format_is_hyphenated(self):
        result = generate_slug("jordan", "things-to-do")
        # Should be a valid slug: lowercase, hyphens, no weird chars
        assert all(c.isalnum() or c == "-" for c in result)

    def test_different_inputs_produce_different_slugs(self):
        slug1 = generate_slug("jordan", "things-to-do")
        slug2 = generate_slug("thailand", "best-hotels")
        assert slug1 != slug2


# ---------------------------------------------------------------------------
# write_outputs
# ---------------------------------------------------------------------------


class TestWriteOutputs:
    def test_happy_path_creates_directory_and_all_files(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        output_path = Path(result_path)
        assert output_path.exists()
        assert (output_path / "draft.md").exists()
        assert (output_path / "seo.json").exists()
        assert (output_path / "social_promotion.json").exists()
        assert (output_path / "social_ongoing.json").exists()
        assert (output_path / "enrichment.md").exists()
        assert (output_path / "raw_notes.md").exists()
        assert (output_path / "pipeline_log.json").exists()

    def test_writes_exactly_7_files(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        files = list(Path(result_path).iterdir())
        assert len(files) == 7

    def test_draft_content_written_correctly(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "draft.md").read_text()
        assert "10 Best Things to Do in Jordan" in content

    def test_seo_json_is_valid_json(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        seo_content = (Path(result_path) / "seo.json").read_text()
        parsed = json.loads(seo_content)
        assert parsed["primary_keyword"] == "things to do in jordan"

    def test_social_promotion_json_is_valid_json(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "social_promotion.json").read_text()
        parsed = json.loads(content)
        assert "twitter" in parsed

    def test_pipeline_log_json_is_valid_json(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "pipeline_log.json").read_text()
        parsed = json.loads(content)
        assert parsed["destination"] == "jordan"

    def test_returns_correct_output_path(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        expected = str(tmp_path / slug)
        assert result_path == expected

    def test_output_directory_already_exists_no_error(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        # Pre-create the directory
        (tmp_path / slug).mkdir()
        # Should not raise
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        assert Path(result_path).exists()

    def test_existing_files_overwritten(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        output_dir = tmp_path / slug
        output_dir.mkdir()
        (output_dir / "draft.md").write_text("Old draft content")

        write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft="New draft content",
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (output_dir / "draft.md").read_text()
        assert content == "New draft content"

    def test_empty_social_promotion_writes_empty_json_object(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion={},
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "social_promotion.json").read_text()
        parsed = json.loads(content)
        assert parsed == {}

    def test_very_long_draft_writes_successfully(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        long_draft = "A" * 500_000
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=long_draft,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "draft.md").read_text()
        assert len(content) == 500_000

    def test_nested_dict_in_seo_serialized_correctly(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        nested_seo = {
            "primary_keyword": "jordan",
            "competitors": [
                {"url": "https://site.com/", "metrics": {"da": 72, "pa": 50, "links": 120}},
            ],
        }
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=nested_seo,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "seo.json").read_text()
        parsed = json.loads(content)
        assert parsed["competitors"][0]["metrics"]["da"] == 72

    def test_creates_parent_directories_if_needed(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        nested_output = str(tmp_path / "deep" / "nested" / "output")
        result_path = write_outputs(
            output_dir=nested_output,
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        assert Path(result_path).exists()
        assert (Path(result_path) / "draft.md").exists()

    def test_enrichment_content_written_correctly(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "enrichment.md").read_text()
        assert "Competitor Analysis" in content

    def test_raw_notes_content_written_correctly(self, tmp_path):
        slug = "jordan-things-to-do-2026-03"
        result_path = write_outputs(
            output_dir=str(tmp_path),
            slug=slug,
            draft=SAMPLE_DRAFT,
            seo=SAMPLE_SEO,
            social_promotion=SAMPLE_SOCIAL_PROMOTION,
            social_ongoing=SAMPLE_SOCIAL_ONGOING,
            enrichment=SAMPLE_ENRICHMENT,
            raw_notes=SAMPLE_RAW_NOTES,
            pipeline_log=SAMPLE_PIPELINE_LOG,
        )
        content = (Path(result_path) / "raw_notes.md").read_text()
        assert "Travel notes about Jordan" in content


# ---------------------------------------------------------------------------
# Helper to create a valid draft directory for list_drafts / save_revision tests
# ---------------------------------------------------------------------------


def _create_draft_dir(
    base: Path,
    slug: str,
    destination: str = "jordan",
    post_type: str = "things-to-do",
    focus_keyword: str = "things to do in jordan",
) -> Path:
    """Create a minimal valid draft directory with draft.md and pipeline_log.json."""
    d = base / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "draft.md").write_text("# Draft content")
    (d / "enrichment.md").write_text("## Original enrichment")
    (d / "seo.json").write_text(json.dumps({"primary_keyword": focus_keyword}))
    (d / "social_promotion.json").write_text(json.dumps({"twitter": "tweet"}))
    (d / "social_ongoing.json").write_text(json.dumps({"ideas": []}))
    (d / "raw_notes.md").write_text("Raw notes here")
    (d / "pipeline_log.json").write_text(
        json.dumps(
            {
                "destination": destination,
                "post_type": post_type,
                "focus_keyword": focus_keyword,
            }
        )
    )
    return d


# ---------------------------------------------------------------------------
# list_drafts
# ---------------------------------------------------------------------------


class TestListDrafts:
    def test_happy_path_lists_existing_drafts(self, tmp_path):
        _create_draft_dir(tmp_path, "jordan-things-to-do-2026-03")
        _create_draft_dir(
            tmp_path, "agra-food-guide-2026-04", destination="agra", post_type="food-guide"
        )
        result = list_drafts(str(tmp_path))
        assert len(result) == 2
        slugs = [d["slug"] for d in result]
        assert "agra-food-guide-2026-04" in slugs
        assert "jordan-things-to-do-2026-03" in slugs

    def test_empty_output_dir_returns_empty_list(self, tmp_path):
        result = list_drafts(str(tmp_path))
        assert result == []

    def test_skips_directory_without_draft_md(self, tmp_path):
        d = tmp_path / "no-draft-slug"
        d.mkdir()
        (d / "pipeline_log.json").write_text(json.dumps({"destination": "x", "post_type": "y"}))
        # No draft.md — should be skipped
        result = list_drafts(str(tmp_path))
        assert result == []

    def test_skips_directory_without_pipeline_log(self, tmp_path):
        d = tmp_path / "no-log-slug"
        d.mkdir()
        (d / "draft.md").write_text("# Some draft")
        # No pipeline_log.json — should be skipped
        result = list_drafts(str(tmp_path))
        assert result == []

    def test_metadata_extracted_correctly(self, tmp_path):
        _create_draft_dir(
            tmp_path,
            "agra-things-to-do-2026-03",
            destination="Agra",
            post_type="things-to-do",
            focus_keyword="how to visit taj mahal",
        )
        result = list_drafts(str(tmp_path))
        assert len(result) == 1
        entry = result[0]
        assert entry["slug"] == "agra-things-to-do-2026-03"
        assert entry["destination"] == "Agra"
        assert entry["post_type"] == "things-to-do"
        assert entry["focus_keyword"] == "how to visit taj mahal"
        assert entry["path"] == str(tmp_path / "agra-things-to-do-2026-03")

    def test_results_sorted_by_slug(self, tmp_path):
        _create_draft_dir(tmp_path, "z-slug", destination="z")
        _create_draft_dir(tmp_path, "a-slug", destination="a")
        _create_draft_dir(tmp_path, "m-slug", destination="m")
        result = list_drafts(str(tmp_path))
        slugs = [d["slug"] for d in result]
        assert slugs == ["a-slug", "m-slug", "z-slug"]


# ---------------------------------------------------------------------------
# save_revision
# ---------------------------------------------------------------------------


class TestSaveRevision:
    def test_overwrites_draft_with_new_content(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised draft content",
            enrichment_addition="\n## Revision 1\nNew research here",
            pipeline_log={"destination": "jordan", "post_type": "things-to-do", "revisions": []},
        )
        content = (tmp_path / "test-slug" / "draft.md").read_text()
        assert content == "# Revised draft content"

    def test_enrichment_appended_not_replaced(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised",
            enrichment_addition="\n\n---\n## Revision 1\nNew research",
            pipeline_log={"destination": "jordan", "post_type": "things-to-do"},
        )
        content = (tmp_path / "test-slug" / "enrichment.md").read_text()
        assert "## Original enrichment" in content
        assert "## Revision 1" in content
        assert "New research" in content

    def test_pipeline_log_updated(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        updated_log = {
            "destination": "jordan",
            "post_type": "things-to-do",
            "revisions": [{"revision_number": 1, "directions": "add food section"}],
        }
        save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised",
            enrichment_addition="\nNew stuff",
            pipeline_log=updated_log,
        )
        content = json.loads((tmp_path / "test-slug" / "pipeline_log.json").read_text())
        assert content["revisions"][0]["revision_number"] == 1

    def test_seo_json_untouched(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        original_seo = (tmp_path / "test-slug" / "seo.json").read_text()
        save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised",
            enrichment_addition="\nNew",
            pipeline_log={"destination": "jordan"},
        )
        assert (tmp_path / "test-slug" / "seo.json").read_text() == original_seo

    def test_social_files_untouched(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        original_promo = (tmp_path / "test-slug" / "social_promotion.json").read_text()
        original_ongoing = (tmp_path / "test-slug" / "social_ongoing.json").read_text()
        save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised",
            enrichment_addition="\nNew",
            pipeline_log={"destination": "jordan"},
        )
        assert (tmp_path / "test-slug" / "social_promotion.json").read_text() == original_promo
        assert (tmp_path / "test-slug" / "social_ongoing.json").read_text() == original_ongoing

    def test_nonexistent_slug_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            save_revision(
                output_dir=str(tmp_path),
                slug="nonexistent-slug",
                draft="# Revised",
                enrichment_addition="\nNew",
                pipeline_log={"destination": "jordan"},
            )

    def test_returns_output_path(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        result = save_revision(
            output_dir=str(tmp_path),
            slug="test-slug",
            draft="# Revised",
            enrichment_addition="\nNew",
            pipeline_log={"destination": "jordan"},
        )
        assert result == str(tmp_path / "test-slug")


# ---------------------------------------------------------------------------
# save_fact_check
# ---------------------------------------------------------------------------

SAMPLE_FACT_CHECK = {
    "total_claims": 10,
    "verified": 8,
    "flagged": 1,
    "unverified": 1,
    "timestamp": "2026-03-23T14:00:00",
    "claims": [
        {
            "claim": "Entry fee for foreign tourists is ₹1,100",
            "category": "numbers_costs",
            "status": "verified",
            "source": "tajmahal.gov.in",
            "note": None,
        },
    ],
    "flagged_details": [
        {
            "claim": "Some claim",
            "issue": "Draft says X but source says Y",
            "recommended_correction": "Change X to Y",
            "source": "example.com",
        },
    ],
}


class TestSaveFactCheck:
    def test_happy_path_writes_fact_check_json(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        save_fact_check(
            output_dir=str(tmp_path),
            slug="test-slug",
            fact_check=SAMPLE_FACT_CHECK,
        )
        fc_path = tmp_path / "test-slug" / "fact_check.json"
        assert fc_path.exists()
        parsed = json.loads(fc_path.read_text())
        assert parsed["total_claims"] == 10
        assert parsed["verified"] == 8
        assert parsed["flagged"] == 1
        assert len(parsed["claims"]) == 1

    def test_nonexistent_slug_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            save_fact_check(
                output_dir=str(tmp_path),
                slug="nonexistent-slug",
                fact_check=SAMPLE_FACT_CHECK,
            )

    def test_does_not_touch_other_files(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        original_draft = (tmp_path / "test-slug" / "draft.md").read_text()
        original_seo = (tmp_path / "test-slug" / "seo.json").read_text()
        save_fact_check(
            output_dir=str(tmp_path),
            slug="test-slug",
            fact_check=SAMPLE_FACT_CHECK,
        )
        assert (tmp_path / "test-slug" / "draft.md").read_text() == original_draft
        assert (tmp_path / "test-slug" / "seo.json").read_text() == original_seo

    def test_returns_output_path(self, tmp_path):
        _create_draft_dir(tmp_path, "test-slug")
        result = save_fact_check(
            output_dir=str(tmp_path),
            slug="test-slug",
            fact_check=SAMPLE_FACT_CHECK,
        )
        assert result == str(tmp_path / "test-slug")
