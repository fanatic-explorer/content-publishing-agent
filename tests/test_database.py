"""Tests for src/database.py — comprehensive TDD test suite."""

import sqlite3
from pathlib import Path

import pytest

from src.database import (
    check_processed,
    get_post_history,
    init_db,
    save_pipeline_step,
    save_post_record,
    update_post_status,
)


@pytest.fixture
def db_path(tmp_path):
    """Provide a fresh temporary database path for each test."""
    return str(tmp_path / "test_publishing.db")


@pytest.fixture
def db(db_path):
    """Initialize DB and return path."""
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


class TestInitDb:
    def test_creates_file_if_not_exists(self, tmp_path):
        path = str(tmp_path / "new.db")
        assert not Path(path).exists()
        init_db(path)
        assert Path(path).exists()

    def test_creates_processed_posts_table(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "processed_posts" in tables

    def test_creates_pipeline_runs_table(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "pipeline_runs" in tables

    def test_processed_posts_has_expected_columns(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(processed_posts)")}
        conn.close()
        expected = {
            "id",
            "destination",
            "post_type",
            "status",
            "output_dir",
            "started_at",
            "completed_at",
            "error_message",
        }
        assert expected.issubset(cols)

    def test_pipeline_runs_has_expected_columns(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pipeline_runs)")}
        conn.close()
        expected = {
            "id",
            "post_id",
            "step_name",
            "status",
            "started_at",
            "completed_at",
            "error_message",
        }
        assert expected.issubset(cols)

    def test_wal_mode_enabled(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_idempotent_on_existing_db(self, db):
        """Calling init_db twice must not raise or corrupt the schema."""
        init_db(db)  # second call — should not error

    def test_unique_constraint_on_destination_post_type(self, db):
        """processed_posts must have a UNIQUE constraint on (destination, post_type)."""
        conn = sqlite3.connect(db)
        # Insert first row directly
        conn.execute(
            "INSERT INTO processed_posts (destination, post_type, status, output_dir) "
            "VALUES (?, ?, ?, ?)",
            ("jordan", "things-to-do", "completed", "/output/jordan"),
        )
        conn.commit()
        # Second insert with same (destination, post_type) should violate constraint
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO processed_posts (destination, post_type, status, output_dir) "
                "VALUES (?, ?, ?, ?)",
                ("jordan", "things-to-do", "in_progress", "/output/jordan2"),
            )
            conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# save_post_record
# ---------------------------------------------------------------------------


class TestSavePostRecord:
    def test_happy_path_inserts_row(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        assert isinstance(row_id, int)
        assert row_id > 0
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()[0]
        conn.close()
        assert count == 1

    def test_returns_row_id(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT id FROM processed_posts WHERE destination=? AND post_type=?",
            ("jordan", "things-to-do"),
        ).fetchone()
        conn.close()
        assert row[0] == row_id

    def test_duplicate_destination_post_type_updates_not_errors(self, db):
        """Inserting the same (destination, post_type) twice should update, not raise."""
        row_id_1 = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/v1")
        row_id_2 = save_post_record(db, "jordan", "things-to-do", "completed", "/output/v2")
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()[0]
        row = conn.execute(
            "SELECT status, output_dir FROM processed_posts WHERE destination=? AND post_type=?",
            ("jordan", "things-to-do"),
        ).fetchone()
        conn.close()
        assert count == 1
        assert row[0] == "completed"
        assert row[1] == "/output/v2"
        # Both calls should return a valid id
        assert isinstance(row_id_1, int)
        assert isinstance(row_id_2, int)

    def test_different_post_types_create_separate_rows(self, db):
        save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/1")
        save_post_record(db, "jordan", "best-hotels", "in_progress", "/output/2")
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()[0]
        conn.close()
        assert count == 2

    def test_empty_strings_for_destination_and_post_type(self, db):
        """Empty strings should be stored without error."""
        row_id = save_post_record(db, "", "", "in_progress", "/output/empty")
        assert isinstance(row_id, int)

    def test_sql_injection_in_destination_name(self, db):
        """SQL injection attempts in destination names should be safely parameterized."""
        malicious = "'; DROP TABLE processed_posts; --"
        row_id = save_post_record(db, malicious, "things-to-do", "in_progress", "/output/evil")
        assert isinstance(row_id, int)
        # Table should still exist
        conn = sqlite3.connect(db)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "processed_posts" in tables


# ---------------------------------------------------------------------------
# check_processed
# ---------------------------------------------------------------------------


class TestCheckProcessed:
    def test_returns_false_when_no_data(self, db):
        result = check_processed(db, "jordan", "things-to-do")
        assert result is False

    def test_returns_true_when_completed(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/jordan")
        result = check_processed(db, "jordan", "things-to-do")
        assert result is True

    def test_returns_false_when_in_progress(self, db):
        save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        result = check_processed(db, "jordan", "things-to-do")
        assert result is False

    def test_returns_false_when_failed(self, db):
        save_post_record(db, "jordan", "things-to-do", "failed", "/output/jordan")
        result = check_processed(db, "jordan", "things-to-do")
        assert result is False

    def test_returns_false_for_different_post_type(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/jordan")
        result = check_processed(db, "jordan", "best-hotels")
        assert result is False

    def test_returns_false_for_different_destination(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/jordan")
        result = check_processed(db, "thailand", "things-to-do")
        assert result is False


# ---------------------------------------------------------------------------
# update_post_status
# ---------------------------------------------------------------------------


class TestUpdatePostStatus:
    def test_updates_status_to_completed(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        update_post_status(db, row_id, "completed")
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT status FROM processed_posts WHERE id=?", (row_id,)).fetchone()
        conn.close()
        assert row[0] == "completed"

    def test_updates_status_to_failed_with_error_message(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        update_post_status(db, row_id, "failed", error_message="API timeout")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT status, error_message FROM processed_posts WHERE id=?", (row_id,)
        ).fetchone()
        conn.close()
        assert row[0] == "failed"
        assert row[1] == "API timeout"

    def test_updates_status_without_error_message(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        update_post_status(db, row_id, "completed")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT error_message FROM processed_posts WHERE id=?", (row_id,)
        ).fetchone()
        conn.close()
        assert row[0] is None

    def test_status_transition_in_progress_to_completed(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        update_post_status(db, row_id, "completed")
        assert check_processed(db, "jordan", "things-to-do") is True

    def test_status_transition_in_progress_to_failed(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        update_post_status(db, row_id, "failed", error_message="Network error")
        assert check_processed(db, "jordan", "things-to-do") is False


# ---------------------------------------------------------------------------
# save_pipeline_step
# ---------------------------------------------------------------------------


class TestSavePipelineStep:
    def test_happy_path_inserts_step(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        save_pipeline_step(db, row_id, "keyword_research", "completed")
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        conn.close()
        assert count == 1

    def test_multiple_steps_for_same_post(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        save_pipeline_step(db, row_id, "keyword_research", "completed")
        save_pipeline_step(db, row_id, "draft_writing", "completed")
        save_pipeline_step(db, row_id, "seo_optimization", "in_progress")
        conn = sqlite3.connect(db)
        count = conn.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE post_id=?", (row_id,)
        ).fetchone()[0]
        conn.close()
        assert count == 3

    def test_step_with_error_message(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        save_pipeline_step(db, row_id, "browser_fetch", "failed", error_message="Timeout after 30s")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT step_name, status, error_message FROM pipeline_runs WHERE post_id=?",
            (row_id,),
        ).fetchone()
        conn.close()
        assert row[0] == "browser_fetch"
        assert row[1] == "failed"
        assert row[2] == "Timeout after 30s"

    def test_step_without_error_message(self, db):
        row_id = save_post_record(db, "jordan", "things-to-do", "in_progress", "/output/jordan")
        save_pipeline_step(db, row_id, "keyword_research", "completed")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT error_message FROM pipeline_runs WHERE post_id=?", (row_id,)
        ).fetchone()
        conn.close()
        assert row[0] is None


# ---------------------------------------------------------------------------
# get_post_history
# ---------------------------------------------------------------------------


class TestGetPostHistory:
    def test_returns_empty_list_for_unknown_destination(self, db):
        result = get_post_history(db, "unknown-destination")
        assert result == []

    def test_returns_all_posts_for_destination(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/1")
        save_post_record(db, "jordan", "best-hotels", "completed", "/output/2")
        save_post_record(db, "thailand", "things-to-do", "completed", "/output/3")
        result = get_post_history(db, "jordan")
        assert len(result) == 2

    def test_returns_list_of_dicts(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/jordan")
        result = get_post_history(db, "jordan")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_returned_dicts_have_expected_keys(self, db):
        save_post_record(db, "jordan", "things-to-do", "completed", "/output/jordan")
        result = get_post_history(db, "jordan")
        row = result[0]
        assert "destination" in row
        assert "post_type" in row
        assert "status" in row

    def test_read_only_no_side_effects(self, db):
        """Calling get_post_history must not write anything."""
        conn = sqlite3.connect(db)
        initial_count = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()[0]
        conn.close()
        get_post_history(db, "unknown")
        conn = sqlite3.connect(db)
        final_count = conn.execute("SELECT COUNT(*) FROM processed_posts").fetchone()[0]
        conn.close()
        assert initial_count == final_count
