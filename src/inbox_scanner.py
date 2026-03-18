"""Filesystem scanning for inbox destination folders.

Provides utilities to discover destination subfolders within an inbox directory
and read the text content of files inside each destination folder.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def list_destinations(inbox_dir: str) -> list[str]:
    """Return a sorted list of destination subfolder names in the inbox directory.

    Ignores files at the root level, hidden folders (starting with '.'),
    and .gitkeep entries.

    Args:
        inbox_dir: Absolute or relative path to the inbox directory.

    Returns:
        Sorted list of subfolder names (not full paths).
    """
    inbox_path = Path(inbox_dir)
    logger.debug(f"Scanning inbox directory: {inbox_path}")

    destinations = [entry.name for entry in inbox_path.iterdir() if _is_visible_directory(entry)]

    destinations.sort()
    logger.debug(f"Found {len(destinations)} destination(s): {destinations}")
    return destinations


def read_destination(inbox_dir: str, destination: str) -> dict:
    """Read all .txt and .md files from a destination subfolder.

    Reads only top-level files; does not recurse into nested subfolders.
    Files are sorted alphabetically by name.

    Args:
        inbox_dir: Absolute or relative path to the inbox directory.
        destination: Name of the destination subfolder to read.

    Returns:
        A dict with keys:
            - "destination": the destination name (str)
            - "files": list of dicts, each with "name" (str) and "content" (str)
            - "combined_content": all file contents joined into a single string

    Raises:
        FileNotFoundError: If the destination subfolder does not exist.
    """
    dest_path = Path(inbox_dir) / destination

    if not dest_path.exists():
        logger.error(f"Destination folder not found: {dest_path}")
        raise FileNotFoundError(f"Destination folder not found: {dest_path}")

    logger.debug(f"Reading destination folder: {dest_path}")

    file_entries = sorted(
        (entry for entry in dest_path.iterdir() if _is_readable_content_file(entry)),
        key=lambda e: e.name,
    )

    files = [{"name": entry.name, "content": _read_file(entry)} for entry in file_entries]

    combined_content = "\n".join(f["content"] for f in files)

    logger.debug(f"Read {len(files)} file(s) from destination '{destination}'")

    return {
        "destination": destination,
        "files": files,
        "combined_content": combined_content,
    }


def _is_visible_directory(entry: "os.DirEntry[str] | Path") -> bool:
    """Return True if the entry is a non-hidden directory.

    Args:
        entry: A filesystem entry (os.DirEntry or Path).

    Returns:
        True if the entry is a directory and does not start with '.'.
    """
    name = entry.name if hasattr(entry, "name") else os.path.basename(str(entry))
    return (not name.startswith(".")) and (
        entry.is_dir() if callable(entry.is_dir) else Path(str(entry)).is_dir()
    )


def _is_readable_content_file(entry: "os.DirEntry[str] | Path") -> bool:
    """Return True if the entry is a top-level .txt or .md file (not a directory).

    Args:
        entry: A filesystem entry (os.DirEntry or Path).

    Returns:
        True if the entry is a regular file with a .txt or .md extension.
    """
    if entry.is_dir():
        return False
    suffix = Path(entry.name).suffix.lower()
    return suffix in {".txt", ".md"}


def _read_file(file_path: Path) -> str:
    """Read and return the text content of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        The decoded text content of the file.

    Raises:
        OSError: If the file cannot be read.
    """
    logger.debug(f"Reading file: {file_path}")
    return file_path.read_text(encoding="utf-8")
