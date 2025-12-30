"""
Unit tests for VaultManager (app/vault/manager.py)
"""
import pytest
from pathlib import Path
from datetime import datetime
import re
from app.vault.manager import VaultManager


@pytest.mark.unit
@pytest.mark.manager
class TestVaultManager:
    """Test VaultManager functionality"""

    def test_manager_initialization(self, temp_vault_path):
        """Test manager initializes correctly"""
        manager = VaultManager(temp_vault_path)
        assert manager.vault_path == temp_vault_path
        assert manager.parser is not None

    def test_create_note_basic(self, empty_vault_manager):
        """Test creating a basic note"""
        note = empty_vault_manager.create_note(
            path="test.md",
            content="Test content",
            frontmatter={"title": "Test"}
        )

        assert note["path"] == "test.md"
        assert note["title"] == "Test"
        assert note["content"] == "Test content"
        assert (empty_vault_manager.vault_path / "test.md").exists()

    def test_create_note_in_subfolder(self, empty_vault_manager):
        """Test creating note in subfolder"""
        note = empty_vault_manager.create_note(
            path="folder/test.md",
            content="Test content",
            frontmatter={"title": "Test"}
        )

        assert note["path"] == "folder/test.md"
        assert (empty_vault_manager.vault_path / "folder" / "test.md").exists()

    def test_create_note_duplicate(self, vault_manager):
        """Test creating duplicate note raises error"""
        with pytest.raises(FileExistsError):
            vault_manager.create_note(
                path="Welcome.md",
                content="Duplicate",
                frontmatter={}
            )

    def test_create_note_with_tags(self, empty_vault_manager):
        """Test creating note with tags"""
        note = empty_vault_manager.create_note(
            path="test.md",
            content="Content",
            frontmatter={"title": "Test", "tags": ["tag1", "tag2"]}
        )

        assert "tag1" in note["tags"]
        assert "tag2" in note["tags"]

    def test_read_note(self, vault_manager):
        """Test reading an existing note"""
        note = vault_manager.read_note("Welcome.md")

        assert note["path"] == "Welcome.md"
        assert note["title"] == "Welcome"
        assert "Welcome to the Test Vault" in note["content"]
        assert "meta" in note["tags"]

    def test_read_note_not_found(self, vault_manager):
        """Test reading non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.read_note("nonexistent.md")

    def test_read_note_with_links(self, vault_manager):
        """Test reading note extracts links"""
        note = vault_manager.read_note("Welcome.md")

        assert "wiki_links" in note
        assert "Projects" in note["wiki_links"]
        assert "Ideas" in note["wiki_links"]

    def test_update_note_content(self, vault_manager):
        """Test updating note content"""
        note = vault_manager.update_note(
            path="Welcome.md",
            content="Updated content"
        )

        assert note["content"] == "Updated content"
        # Frontmatter should be preserved
        assert note["title"] == "Welcome"

    def test_update_note_frontmatter(self, vault_manager):
        """Test updating note frontmatter"""
        note = vault_manager.update_note(
            path="Welcome.md",
            frontmatter={"title": "Welcome", "new_field": "value"}
        )

        assert note["frontmatter"]["new_field"] == "value"
        assert note["title"] == "Welcome"

    def test_update_note_append(self, vault_manager):
        """Test appending content to note"""
        original = vault_manager.read_note("Welcome.md")
        original_content = original["content"]

        note = vault_manager.update_note(
            path="Welcome.md",
            content="Appended content",
            append=True
        )

        assert original_content in note["content"]
        assert "Appended content" in note["content"]

    def test_update_note_not_found(self, vault_manager):
        """Test updating non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.update_note(
                path="nonexistent.md",
                content="New content"
            )

    def test_delete_note(self, vault_manager):
        """Test deleting a note"""
        vault_manager.delete_note("Orphan Note.md")

        assert not (vault_manager.vault_path / "Orphan Note.md").exists()

    def test_delete_note_not_found(self, vault_manager):
        """Test deleting non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.delete_note("nonexistent.md")

    def test_delete_note_invalidates_cache(self, vault_manager):
        """Test deletion invalidates caches"""
        # Build caches
        vault_manager.parser.build_title_map()
        vault_manager.parser.build_backlinks_index()

        assert vault_manager.parser._title_map is not None
        assert vault_manager.parser._backlinks_index is not None

        # Delete note
        vault_manager.delete_note("Orphan Note.md")

        # Caches should be invalidated
        assert vault_manager.parser._title_map is None
        assert vault_manager.parser._backlinks_index is None

    def test_move_note(self, vault_manager):
        """Test moving/renaming a note"""
        note = vault_manager.move_note(
            old_path="Orphan Note.md",
            new_path="Renamed Note.md"
        )

        assert note["path"] == "Renamed Note.md"
        assert not (vault_manager.vault_path / "Orphan Note.md").exists()
        assert (vault_manager.vault_path / "Renamed Note.md").exists()

    def test_move_note_to_subfolder(self, vault_manager):
        """Test moving note to subfolder"""
        note = vault_manager.move_note(
            old_path="Orphan Note.md",
            new_path="archive/Orphan Note.md"
        )

        assert note["path"] == "archive/Orphan Note.md"
        assert (vault_manager.vault_path / "archive" / "Orphan Note.md").exists()

    def test_move_note_destination_exists(self, vault_manager):
        """Test moving to existing destination"""
        with pytest.raises(FileExistsError):
            vault_manager.move_note(
                old_path="Orphan Note.md",
                new_path="Welcome.md"
            )

    def test_move_note_source_not_found(self, vault_manager):
        """Test moving non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.move_note(
                old_path="nonexistent.md",
                new_path="new.md"
            )

    def test_search_notes_basic(self, vault_manager):
        """Test basic search"""
        results = vault_manager.search_notes(query="vault")

        assert len(results) > 0
        assert any("Welcome" in r["title"] for r in results)

    def test_search_notes_case_insensitive(self, vault_manager):
        """Test case-insensitive search"""
        results1 = vault_manager.search_notes(query="VAULT")
        results2 = vault_manager.search_notes(query="vault")

        assert len(results1) == len(results2)

    def test_search_notes_with_tags(self, vault_manager):
        """Test search with tag filter"""
        results = vault_manager.search_notes(query="", tags=["meta"])

        assert len(results) > 0
        assert all("meta" in r["tags"] for r in results)

    def test_search_notes_with_limit(self, vault_manager):
        """Test search with result limit"""
        results = vault_manager.search_notes(query="", limit=2)

        assert len(results) <= 2

    def test_search_notes_with_regex(self, vault_manager):
        """Test search with regex pattern"""
        results = vault_manager.search_notes(
            query=r"\[\[.*?\]\]",  # Find notes with wiki-links
            use_regex=True
        )

        assert len(results) > 0

    def test_search_notes_invalid_regex(self, vault_manager):
        """Test search with invalid regex pattern"""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            vault_manager.search_notes(
                query="[invalid",
                use_regex=True
            )

    def test_list_notes_basic(self, vault_manager):
        """Test listing all notes"""
        notes = vault_manager.list_notes()

        assert len(notes) >= 7  # Sample vault has 8 notes
        assert all("path" in n for n in notes)
        assert all("title" in n for n in notes)

    def test_list_notes_non_recursive(self, vault_manager):
        """Test listing notes non-recursively"""
        notes = vault_manager.list_notes(recursive=False)

        # Should not include nested note
        assert not any("subfolder" in n["path"] for n in notes)

    def test_list_notes_with_directory(self, vault_manager):
        """Test listing notes in specific directory"""
        notes = vault_manager.list_notes(directory="subfolder")

        assert len(notes) > 0
        assert all("subfolder" in n["path"] for n in notes)

    def test_list_notes_with_frontmatter(self, vault_manager):
        """Test listing with frontmatter included"""
        notes = vault_manager.list_notes(include_frontmatter=True)

        assert all("frontmatter" in n for n in notes)

    def test_list_notes_sort_by_modified(self, vault_manager):
        """Test sorting by modification time"""
        notes = vault_manager.list_notes(sort_by="modified")

        # Should have modified timestamps
        assert all("modified" in n for n in notes)

    def test_list_notes_sort_by_created(self, vault_manager):
        """Test sorting by creation time"""
        notes = vault_manager.list_notes(sort_by="created")

        assert all("created" in n for n in notes)

    def test_list_notes_sort_by_title(self, vault_manager):
        """Test sorting by title"""
        notes = vault_manager.list_notes(sort_by="title")

        titles = [n["title"] for n in notes]
        assert titles == sorted(titles)

    def test_list_notes_sort_by_size(self, vault_manager):
        """Test sorting by file size"""
        notes = vault_manager.list_notes(sort_by="size")

        assert all("size" in n for n in notes)

    def test_list_notes_with_limit_offset(self, vault_manager):
        """Test pagination with limit and offset"""
        all_notes = vault_manager.list_notes()
        paginated = vault_manager.list_notes(limit=2, offset=1)

        assert len(paginated) <= 2
        assert paginated[0]["path"] != all_notes[0]["path"]

    def test_get_note_metadata(self, vault_manager):
        """Test getting note metadata"""
        metadata = vault_manager.get_note_metadata("Welcome")

        assert metadata["title"] == "Welcome"
        assert metadata["path"] == "Welcome.md"
        assert "meta" in metadata["tags"]
        assert "content" not in metadata  # Should not include full content

    def test_get_note_metadata_not_found(self, vault_manager):
        """Test getting metadata for non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.get_note_metadata("Nonexistent")

    def test_get_daily_note_today(self, vault_manager):
        """Test getting/creating today's daily note"""
        today = datetime.now().strftime("%Y-%m-%d")
        note = vault_manager.get_daily_note()

        assert note["title"] == today
        assert note["path"] == f"{today}.md"
        assert "daily-note" in note["tags"]

    def test_get_daily_note_specific_date(self, vault_manager):
        """Test getting daily note for specific date"""
        date = "2025-12-25"
        note = vault_manager.get_daily_note(date)

        assert note["title"] == date
        assert note["path"] == f"{date}.md"

    def test_get_daily_note_invalid_date(self, vault_manager):
        """Test getting daily note with invalid date"""
        with pytest.raises(ValueError):
            vault_manager.get_daily_note("invalid-date")

    def test_get_daily_note_existing(self, vault_manager):
        """Test getting existing daily note"""
        date = "2025-01-01"

        # Create it first
        vault_manager.get_daily_note(date)

        # Get it again
        note = vault_manager.get_daily_note(date)

        assert note["title"] == date

    def test_get_backlinks(self, vault_manager):
        """Test getting backlinks for a note"""
        result = vault_manager.get_backlinks("Projects")

        assert result["note_path"] == "Projects.md"
        assert result["note_name"] == "Projects"
        assert result["backlink_count"] >= 2
        assert len(result["backlinks"]) >= 2

    def test_get_backlinks_no_backlinks(self, vault_manager):
        """Test getting backlinks for orphan note"""
        result = vault_manager.get_backlinks("Orphan Note")

        assert result["backlink_count"] == 0
        assert len(result["backlinks"]) == 0

    def test_get_backlinks_not_found(self, vault_manager):
        """Test getting backlinks for non-existent note"""
        with pytest.raises(FileNotFoundError):
            vault_manager.get_backlinks("Nonexistent")

    def test_get_orphan_notes(self, vault_manager):
        """Test finding orphan notes"""
        orphans = vault_manager.get_orphan_notes()

        assert len(orphans) > 0
        # Orphan Note should be in results
        assert any(o["name"] == "Orphan Note" for o in orphans)

    def test_get_orphan_notes_with_limit(self, vault_manager):
        """Test finding orphans with limit"""
        orphans = vault_manager.get_orphan_notes(limit=1)

        assert len(orphans) <= 1

    def test_get_note_graph_full(self, vault_manager):
        """Test getting full note graph"""
        graph = vault_manager.get_note_graph()

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) > 0
        assert len(graph["edges"]) > 0

    def test_get_note_graph_centered(self, vault_manager):
        """Test getting graph centered on specific note"""
        graph = vault_manager.get_note_graph(center_note="Welcome")

        # Should include Welcome node
        assert any(n["name"] == "Welcome" for n in graph["nodes"])

    def test_get_note_graph_with_depth(self, vault_manager):
        """Test graph with depth limit"""
        graph_depth1 = vault_manager.get_note_graph(center_note="Welcome", depth=1)
        graph_depth2 = vault_manager.get_note_graph(center_note="Welcome", depth=2)

        # Deeper graph should have more nodes
        assert len(graph_depth2["nodes"]) >= len(graph_depth1["nodes"])

    def test_get_note_graph_max_nodes(self, vault_manager):
        """Test graph with max nodes limit"""
        graph = vault_manager.get_note_graph(max_nodes=3)

        assert len(graph["nodes"]) <= 3

    def test_get_note_graph_node_structure(self, vault_manager):
        """Test graph node structure"""
        graph = vault_manager.get_note_graph(center_note="Welcome", depth=1)

        for node in graph["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "path" in node
            assert "tags" in node
            assert "outgoing_links" in node
            assert "backlinks" in node

    def test_get_note_graph_edge_structure(self, vault_manager):
        """Test graph edge structure"""
        graph = vault_manager.get_note_graph(center_note="Welcome", depth=1)

        for edge in graph["edges"]:
            assert "source" in edge
            assert "target" in edge

    def test_cache_invalidation_on_create(self, vault_manager):
        """Test caches are invalidated on note creation"""
        # Build caches
        vault_manager.parser.build_title_map()
        vault_manager.parser.build_backlinks_index()

        assert vault_manager.parser._title_map is not None
        assert vault_manager.parser._backlinks_index is not None

        # Create note
        vault_manager.create_note(
            path="new.md",
            content="New note",
            frontmatter={}
        )

        # Caches should be invalidated
        assert vault_manager.parser._title_map is None
        assert vault_manager.parser._backlinks_index is None

    def test_cache_invalidation_on_update(self, vault_manager):
        """Test caches are invalidated on note update"""
        vault_manager.parser.build_title_map()
        vault_manager.parser.build_backlinks_index()

        vault_manager.update_note(
            path="Welcome.md",
            content="Updated"
        )

        assert vault_manager.parser._backlinks_index is None

    def test_cache_invalidation_on_move(self, vault_manager):
        """Test caches are invalidated on note move"""
        vault_manager.parser.build_title_map()
        vault_manager.parser.build_backlinks_index()

        vault_manager.move_note(
            old_path="Orphan Note.md",
            new_path="Moved.md"
        )

        assert vault_manager.parser._title_map is None
        assert vault_manager.parser._backlinks_index is None

    def test_note_structure_consistency(self, vault_manager):
        """Test all note operations return consistent structure"""
        # Create
        created = vault_manager.create_note(
            path="test.md",
            content="Content",
            frontmatter={"title": "Test"}
        )

        # Read
        read = vault_manager.read_note("test.md")

        # Update
        updated = vault_manager.update_note(
            path="test.md",
            content="Updated"
        )

        # All should have same basic structure
        for note in [created, read, updated]:
            assert "path" in note
            assert "title" in note
            assert "content" in note
            assert "frontmatter" in note
            assert "tags" in note
            assert "size" in note
            assert "modified" in note
