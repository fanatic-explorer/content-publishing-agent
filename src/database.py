"""database.py — All SQLite read/write operations for the Content Publishing Pipeline Agent.

Owns a single SQLite file at the path supplied by callers. Schema:
  - processed_posts: one row per (destination, post_type) tracking publishing status
  - pipeline_runs: audit log of individual pipeline step executions
"""

import logging
import sqlite3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL_PROCESSED_POSTS = """
CREATE TABLE IF NOT EXISTS processed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    destination TEXT NOT NULL,
    post_type TEXT NOT NULL,
    status TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    error_message TEXT,
    UNIQUE (destination, post_type)
)
"""

_DDL_PIPELINE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    error_message TEXT
)
"""


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def init_db(db_path: str) -> None:
    """Initialise the SQLite database, creating tables if they don't exist.

    Sets WAL journal mode for better concurrent read performance. Safe to call
    multiple times — all DDL statements use IF NOT EXISTS.

    Args:
        db_path: Filesystem path to the SQLite database file.

    Raises:
        sqlite3.Error: If the database cannot be initialised.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(_DDL_PROCESSED_POSTS)
            conn.execute(_DDL_PIPELINE_RUNS)
            conn.commit()
        logger.info(f"Database initialised at {db_path}")
    except sqlite3.Error as exc:
        logger.error(f"init_db failed for {db_path}: {exc}")
        raise


# ---------------------------------------------------------------------------
# save_post_record
# ---------------------------------------------------------------------------


def save_post_record(
    db_path: str,
    destination: str,
    post_type: str,
    status: str,
    output_dir: str,
) -> int:
    """Insert or update a post record in the processed_posts table.

    Uses INSERT OR REPLACE so that calling this twice with the same
    (destination, post_type) updates the existing row rather than raising
    an integrity error.

    Args:
        db_path: Path to the SQLite database file.
        destination: The publishing destination (e.g. "jordan").
        post_type: The type of post (e.g. "things-to-do").
        status: Current status string (e.g. "in_progress", "completed", "failed").
        output_dir: Filesystem path to the output directory for this post.

    Returns:
        The integer row id of the inserted or updated row.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    sql = """
        INSERT INTO processed_posts (destination, post_type, status, output_dir)
        VALUES (:destination, :post_type, :status, :output_dir)
        ON CONFLICT (destination, post_type)
        DO UPDATE SET
            status = excluded.status,
            output_dir = excluded.output_dir,
            started_at = datetime('now'),
            completed_at = NULL,
            error_message = NULL
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                sql,
                {
                    "destination": destination,
                    "post_type": post_type,
                    "status": status,
                    "output_dir": output_dir,
                },
            )
            conn.commit()
            row_id = cursor.lastrowid
            if row_id == 0:
                # ON CONFLICT UPDATE — fetch the actual id
                row = conn.execute(
                    "SELECT id FROM processed_posts WHERE destination = :destination AND post_type = :post_type",
                    {"destination": destination, "post_type": post_type},
                ).fetchone()
                row_id = row[0]
        logger.info(
            f"save_post_record: destination={destination} post_type={post_type} id={row_id}"
        )
        return row_id
    except sqlite3.Error as exc:
        logger.error(
            f"save_post_record failed for destination={destination} post_type={post_type}: {exc}"
        )
        raise


# ---------------------------------------------------------------------------
# check_processed
# ---------------------------------------------------------------------------


def check_processed(db_path: str, destination: str, post_type: str) -> bool:
    """Check whether a post has been successfully completed.

    Args:
        db_path: Path to the SQLite database file.
        destination: The publishing destination to check.
        post_type: The post type to check.

    Returns:
        True if a row with status='completed' exists for the given
        (destination, post_type), False otherwise.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    sql = """
        SELECT COUNT(*) FROM processed_posts
        WHERE destination = :destination
          AND post_type = :post_type
          AND status = 'completed'
    """
    try:
        with sqlite3.connect(db_path) as conn:
            count = conn.execute(
                sql,
                {"destination": destination, "post_type": post_type},
            ).fetchone()[0]
        result = count > 0
        logger.debug(
            f"check_processed: destination={destination} post_type={post_type} result={result}"
        )
        return result
    except sqlite3.Error as exc:
        logger.error(
            f"check_processed failed for destination={destination} post_type={post_type}: {exc}"
        )
        raise


# ---------------------------------------------------------------------------
# update_post_status
# ---------------------------------------------------------------------------


def update_post_status(
    db_path: str,
    post_id: int,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update the status (and optionally the error message) of a processed_posts row.

    Also sets completed_at to the current timestamp when called.

    Args:
        db_path: Path to the SQLite database file.
        post_id: The integer primary key of the row to update.
        status: New status value (e.g. "completed", "failed").
        error_message: Optional error detail to store. Pass None to leave it unset.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    sql = """
        UPDATE processed_posts
        SET status = :status,
            completed_at = datetime('now'),
            error_message = :error_message
        WHERE id = :post_id
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                sql,
                {
                    "post_id": post_id,
                    "status": status,
                    "error_message": error_message,
                },
            )
            conn.commit()
        logger.info(f"update_post_status: post_id={post_id} status={status}")
    except sqlite3.Error as exc:
        logger.error(f"update_post_status failed for post_id={post_id}: {exc}")
        raise


# ---------------------------------------------------------------------------
# save_pipeline_step
# ---------------------------------------------------------------------------


def save_pipeline_step(
    db_path: str,
    post_id: int,
    step_name: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Record the outcome of a single pipeline step in the pipeline_runs table.

    Args:
        db_path: Path to the SQLite database file.
        post_id: Foreign key referencing processed_posts.id.
        step_name: Name of the pipeline step (e.g. "keyword_research", "draft_writing").
        status: Outcome of the step (e.g. "completed", "failed", "in_progress").
        error_message: Optional error detail if the step failed.

    Raises:
        sqlite3.Error: If the database operation fails.
    """
    sql = """
        INSERT INTO pipeline_runs (post_id, step_name, status, error_message)
        VALUES (:post_id, :step_name, :status, :error_message)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                sql,
                {
                    "post_id": post_id,
                    "step_name": step_name,
                    "status": status,
                    "error_message": error_message,
                },
            )
            conn.commit()
        logger.info(f"save_pipeline_step: post_id={post_id} step={step_name} status={status}")
    except sqlite3.Error as exc:
        logger.error(f"save_pipeline_step failed for post_id={post_id} step={step_name}: {exc}")
        raise


# ---------------------------------------------------------------------------
# get_post_history
# ---------------------------------------------------------------------------


def get_post_history(db_path: str, destination: str) -> list[dict]:
    """Return all processed_posts rows for a given destination.

    Read-only; performs no writes.

    Args:
        db_path: Path to the SQLite database file.
        destination: The publishing destination to query.

    Returns:
        List of dicts, one per row, containing all columns from processed_posts.
        Returns an empty list if no rows are found.

    Raises:
        sqlite3.Error: If the database query fails.
    """
    sql = """
        SELECT id, destination, post_type, status, output_dir,
               started_at, completed_at, error_message
        FROM processed_posts
        WHERE destination = :destination
        ORDER BY started_at DESC
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, {"destination": destination}).fetchall()
        result = [dict(row) for row in rows]
        logger.debug(f"get_post_history: destination={destination} returned {len(result)} rows")
        return result
    except sqlite3.Error as exc:
        logger.error(f"get_post_history failed for destination={destination}: {exc}")
        raise
