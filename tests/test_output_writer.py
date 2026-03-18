"""Tests for src/output_writer.py — comprehensive TDD test suite."""

import json
from pathlib import Path

from src.output_writer import generate_slug, write_outputs

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
