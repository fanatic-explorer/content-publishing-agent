"""Tests for src/inbox_scanner.py — comprehensive TDD test suite."""

import pytest

from src.inbox_scanner import list_destinations, read_destination

# ---------------------------------------------------------------------------
# list_destinations
# ---------------------------------------------------------------------------


class TestListDestinations:
    def test_returns_sorted_subfolder_names(self, tmp_path):
        (tmp_path / "jordan").mkdir()
        (tmp_path / "thailand").mkdir()
        (tmp_path / "albania").mkdir()
        result = list_destinations(str(tmp_path))
        assert result == ["albania", "jordan", "thailand"]

    def test_empty_inbox_returns_empty_list(self, tmp_path):
        result = list_destinations(str(tmp_path))
        assert result == []

    def test_ignores_files_at_root_level(self, tmp_path):
        (tmp_path / "jordan").mkdir()
        (tmp_path / "notes.txt").write_text("some notes")
        (tmp_path / "README.md").write_text("readme")
        result = list_destinations(str(tmp_path))
        assert result == ["jordan"]

    def test_no_subfolders_only_files_returns_empty_list(self, tmp_path):
        (tmp_path / "notes.txt").write_text("some notes")
        (tmp_path / "data.csv").write_text("a,b,c")
        result = list_destinations(str(tmp_path))
        assert result == []

    def test_ignores_hidden_folders(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "jordan").mkdir()
        result = list_destinations(str(tmp_path))
        assert result == ["jordan"]
        assert ".hidden" not in result
        assert ".git" not in result

    def test_ignores_gitkeep_file(self, tmp_path):
        (tmp_path / ".gitkeep").write_text("")
        (tmp_path / "jordan").mkdir()
        result = list_destinations(str(tmp_path))
        assert result == ["jordan"]

    def test_unicode_folder_names(self, tmp_path):
        (tmp_path / "turquie").mkdir()
        (tmp_path / "japon").mkdir()
        result = list_destinations(str(tmp_path))
        assert "japon" in result
        assert "turquie" in result

    def test_single_subfolder(self, tmp_path):
        (tmp_path / "jordan").mkdir()
        result = list_destinations(str(tmp_path))
        assert result == ["jordan"]

    def test_mixed_hidden_and_visible_folders(self, tmp_path):
        (tmp_path / ".cache").mkdir()
        (tmp_path / "jordan").mkdir()
        (tmp_path / ".DS_Store").write_text("")
        (tmp_path / "thailand").mkdir()
        result = list_destinations(str(tmp_path))
        assert result == ["jordan", "thailand"]


# ---------------------------------------------------------------------------
# read_destination
# ---------------------------------------------------------------------------


class TestReadDestination:
    def test_happy_path_reads_txt_and_md_files(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "notes.txt").write_text("Travel notes about Jordan")
        (dest / "ideas.md").write_text("Blog post ideas")
        result = read_destination(str(tmp_path), "jordan")
        assert result["destination"] == "jordan"
        assert len(result["files"]) == 2
        assert "Travel notes about Jordan" in result["combined_content"]
        assert "Blog post ideas" in result["combined_content"]

    def test_returns_correct_structure(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "notes.txt").write_text("Hello")
        result = read_destination(str(tmp_path), "jordan")
        assert "destination" in result
        assert "files" in result
        assert "combined_content" in result

    def test_files_have_name_and_content_keys(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "notes.txt").write_text("Hello")
        result = read_destination(str(tmp_path), "jordan")
        file_entry = result["files"][0]
        assert "name" in file_entry
        assert "content" in file_entry
        assert file_entry["name"] == "notes.txt"
        assert file_entry["content"] == "Hello"

    def test_ignores_non_txt_and_non_md_files(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "notes.txt").write_text("Notes")
        (dest / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0")
        (dest / "data.csv").write_text("a,b,c")
        (dest / "ideas.md").write_text("Ideas")
        result = read_destination(str(tmp_path), "jordan")
        names = [f["name"] for f in result["files"]]
        assert "notes.txt" in names
        assert "ideas.md" in names
        assert "photo.jpg" not in names
        assert "data.csv" not in names

    def test_empty_folder_returns_empty_files_and_content(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        result = read_destination(str(tmp_path), "jordan")
        assert result["files"] == []
        assert result["combined_content"] == ""

    def test_folder_with_no_txt_or_md_returns_empty(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "photo.jpg").write_bytes(b"\xff\xd8")
        (dest / "data.csv").write_text("a,b")
        result = read_destination(str(tmp_path), "jordan")
        assert result["files"] == []
        assert result["combined_content"] == ""

    def test_destination_not_exists_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_destination(str(tmp_path), "nonexistent")

    def test_files_sorted_alphabetically(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "zebra.txt").write_text("Z")
        (dest / "alpha.md").write_text("A")
        (dest / "middle.txt").write_text("M")
        result = read_destination(str(tmp_path), "jordan")
        names = [f["name"] for f in result["files"]]
        assert names == ["alpha.md", "middle.txt", "zebra.txt"]

    def test_unicode_filenames(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "cafe-notes.txt").write_text("Notes about cafes")
        result = read_destination(str(tmp_path), "jordan")
        assert len(result["files"]) == 1

    def test_very_large_file_content(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        large_content = "A" * 100_000
        (dest / "large.txt").write_text(large_content)
        result = read_destination(str(tmp_path), "jordan")
        assert len(result["files"]) == 1
        assert len(result["combined_content"]) >= 100_000

    def test_nested_subfolders_not_recursed(self, tmp_path):
        """Only top-level files in the destination folder should be read."""
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "notes.txt").write_text("Top level")
        sub = dest / "subfolder"
        sub.mkdir()
        (sub / "deep.txt").write_text("Nested content")
        result = read_destination(str(tmp_path), "jordan")
        names = [f["name"] for f in result["files"]]
        assert "notes.txt" in names
        assert "deep.txt" not in names
        assert "Nested content" not in result["combined_content"]

    def test_combined_content_joins_all_file_contents(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        (dest / "a.txt").write_text("Content A")
        (dest / "b.md").write_text("Content B")
        result = read_destination(str(tmp_path), "jordan")
        assert "Content A" in result["combined_content"]
        assert "Content B" in result["combined_content"]

    def test_destination_field_matches_input(self, tmp_path):
        dest = tmp_path / "jordan"
        dest.mkdir()
        result = read_destination(str(tmp_path), "jordan")
        assert result["destination"] == "jordan"
