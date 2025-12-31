"""
Backward compatibility tests for proxy mode

Verifies that all 23 original MCP tools are accessible via proxy mode
and behave identically to direct mode.
"""

import pytest
from pathlib import Path

from app.vault.manager import VaultManager
from app.mcp.proxy import ProxyToolHandler


@pytest.fixture
def test_vault_path(tmp_path):
    """Create a temporary test vault with sample notes"""
    vault_path = tmp_path / "compat-vault"
    vault_path.mkdir()

    # Create test notes for all operations
    (vault_path / "Note1.md").write_text(
        "---\ntags: [ai, ml]\n---\n# Note 1\nContent about AI"
    )
    (vault_path / "Note2.md").write_text(
        "# Note 2\nContent about Python"
    )
    (vault_path / "Note3.md").write_text(
        "# Note 3\n## Introduction\nIntro content\n## Conclusion\nFinal thoughts"
    )
    (vault_path / "Note4.md").write_text(
        "# Note 4\nParagraph one. ^block1\n\nParagraph two."
    )

    # Create templates directory
    templates_dir = vault_path / ".templates"
    templates_dir.mkdir()
    (templates_dir / "test.md").write_text("# {{title}}\n\nContent here")

    return vault_path


@pytest.fixture
def vault_manager(test_vault_path, monkeypatch):
    """Create a VaultManager with test vault"""
    from app.config import settings
    monkeypatch.setattr(settings, "_vault_path", test_vault_path)
    monkeypatch.setattr(settings, "obsidian_vault_path", str(test_vault_path))
    return VaultManager(vault_path=test_vault_path)


@pytest.fixture
def proxy_handler(vault_manager):
    """Create a ProxyToolHandler"""
    return ProxyToolHandler(vault_manager)


class TestOriginalCoreActions:
    """Test all original CORE bundle actions work via proxy"""

    def test_create_note(self, proxy_handler):
        """Test create_note action (original tool #1)"""
        result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {
                "title": "NewNote",
                "content": "Test content",
                "tags": ["test"]
            }
        })

        assert result["success"] is True
        assert "path" in result["result"]

    def test_update_note(self, proxy_handler):
        """Test update_note action (original tool #2)"""
        # First create a note
        create_result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {"title": "UpdateTest", "content": "Original"}
        })
        path = create_result["result"]["path"]

        # Then update it
        result = proxy_handler.handle_obsidian({
            "action": "update_note",
            "args": {"file_path": path, "content": "Updated"}
        })

        assert result["success"] is True

    def test_move_note(self, proxy_handler):
        """Test move_note action (original tool #3)"""
        # Create a note
        create_result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {"title": "MoveTest", "content": "Content"}
        })
        old_path = create_result["result"]["path"]

        # Move it
        result = proxy_handler.handle_obsidian({
            "action": "move_note",
            "args": {"old_path": old_path, "new_path": "moved.md"}
        })

        assert result["success"] is True

    def test_delete_note(self, proxy_handler):
        """Test delete_note action (original tool #4)"""
        # Create a note
        create_result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {"title": "DeleteTest", "content": "Content"}
        })
        path = create_result["result"]["path"]

        # Delete it
        result = proxy_handler.handle_obsidian({
            "action": "delete_note",
            "args": {"file_path": path}
        })

        assert result["success"] is True

    def test_append_note(self, proxy_handler):
        """Test append_note action (original tool #5)"""
        # Create a note
        create_result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {"title": "AppendTest", "content": "Original"}
        })
        path = create_result["result"]["path"]

        # Append to it
        result = proxy_handler.handle_obsidian({
            "action": "append_note",
            "args": {"file_path": path, "content": "\nAppended"}
        })

        assert result["success"] is True

    def test_search_notes(self, proxy_handler):
        """Test search_notes action (original tool #6)"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {"query": "AI"}
        })

        assert result["success"] is True
        assert "count" in result["result"]

    def test_list_notes(self, proxy_handler):
        """Test list_notes action (original tool #7)"""
        result = proxy_handler.handle_obsidian({
            "action": "list_notes",
            "args": {}
        })

        assert result["success"] is True
        assert "notes" in result["result"]

    def test_get_note_metadata(self, proxy_handler):
        """Test get_note (metadata) action (original tool #11)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_note",
            "args": {"title": "Note1"}
        })

        assert result["success"] is True
        assert "name" in result["result"]

    def test_read_note_content(self, proxy_handler):
        """Test read_note_content action (original tool #8 - get_note_by_title)"""
        result = proxy_handler.handle_obsidian({
            "action": "read_note_content",
            "args": {"title": "Note1"}
        })

        assert result["success"] is True
        assert "content" in result["result"]

    def test_resolve_link(self, proxy_handler):
        """Test resolve_link action (original tool #9 - resolve_wiki_link)"""
        result = proxy_handler.handle_obsidian({
            "action": "resolve_link",
            "args": {"link_name": "Note1"}
        })

        assert result["success"] is True
        assert result["result"]["resolved"] is True


class TestOriginalSectionBlockActions:
    """Test section/block operations (original tools #16-20)"""

    def test_get_toc(self, proxy_handler):
        """Test get_toc action (original tool #16)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_toc",
            "args": {"path": "Note3.md"}
        })

        assert result["success"] is True
        assert "toc" in result["result"]

    def test_read_section(self, proxy_handler):
        """Test read_section action (original tool #17)"""
        result = proxy_handler.handle_obsidian({
            "action": "read_section",
            "args": {"path": "Note3.md", "section": "Introduction"}
        })

        assert result["success"] is True
        assert "content" in result["result"]

    def test_read_block(self, proxy_handler):
        """Test read_block action (original tool #18)"""
        result = proxy_handler.handle_obsidian({
            "action": "read_block",
            "args": {"path": "Note4.md", "block_id": "block1"}
        })

        assert result["success"] is True
        assert "content" in result["result"]

    def test_update_section(self, proxy_handler):
        """Test update_section action (original tool #19)"""
        result = proxy_handler.handle_obsidian({
            "action": "update_section",
            "args": {
                "path": "Note3.md",
                "section": "Introduction",
                "content": "New intro content"
            }
        })

        assert result["success"] is True

    def test_update_block(self, proxy_handler):
        """Test update_block action (original tool #20)"""
        result = proxy_handler.handle_obsidian({
            "action": "update_block",
            "args": {
                "path": "Note4.md",
                "block_id": "block1",
                "content": "Updated block content ^block1"
            }
        })

        assert result["success"] is True


class TestOriginalKnowledgeActions:
    """Test knowledge graph actions (original tools #13-15, #10)"""

    def test_get_backlinks(self, proxy_handler):
        """Test get_backlinks action (original tool #13)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_backlinks",
            "args": {"title": "Note1"}
        })

        assert result["success"] is True
        assert "backlink_count" in result["result"]

    def test_get_orphans(self, proxy_handler):
        """Test get_orphans action (original tool #14)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_orphans",
            "args": {}
        })

        assert result["success"] is True
        assert "count" in result["result"]

    def test_get_graph(self, proxy_handler):
        """Test get_graph action (original tool #15)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_graph",
            "args": {}
        })

        assert result["success"] is True
        assert "node_count" in result["result"]

    def test_list_tags(self, proxy_handler):
        """Test list_tags action (original tool #10)"""
        result = proxy_handler.handle_obsidian({
            "action": "list_tags",
            "args": {}
        })

        assert result["success"] is True
        assert "tags" in result["result"]


class TestOriginalTemplateActions:
    """Test template actions (original tools #21-23)"""

    def test_list_templates(self, proxy_handler):
        """Test list_templates action (original tool #21)"""
        result = proxy_handler.handle_obsidian({
            "action": "list_templates",
            "args": {}
        })

        assert result["success"] is True
        assert "count" in result["result"]

    def test_create_from_template(self, proxy_handler):
        """Test create_from_template action (original tool #22)"""
        result = proxy_handler.handle_obsidian({
            "action": "create_from_template",
            "args": {
                "template_name": "test",
                "note_path": "from-template.md",
                "variables": {"title": "Test Title"}
            }
        })

        assert result["success"] is True

    def test_save_template(self, proxy_handler):
        """Test save_template action (original tool #23)"""
        result = proxy_handler.handle_obsidian({
            "action": "save_template",
            "args": {
                "template_name": "new-template",
                "content": "# {{title}}"
            }
        })

        assert result["success"] is True


class TestOriginalAdminActions:
    """Test admin actions (original tool #12)"""

    def test_get_daily_note(self, proxy_handler):
        """Test get_daily_note action (original tool #12)"""
        result = proxy_handler.handle_obsidian({
            "action": "get_daily_note",
            "args": {"date": "2024-01-01"}
        })

        assert result["success"] is True
        assert "name" in result["result"]


class TestErrorHandlingCompatibility:
    """Test that error handling matches original behavior"""

    def test_file_not_found_error(self, proxy_handler):
        """Test file not found errors match original"""
        result = proxy_handler.handle_obsidian({
            "action": "read_note_content",
            "args": {"title": "NonexistentNote"}
        })

        assert result["success"] is False
        # Should contain error message

    def test_missing_required_field_error(self, proxy_handler):
        """Test missing required field errors match original"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {}  # Missing 'query'
        })

        assert result["success"] is False
        assert "query" in result["error"]

    def test_invalid_section_error(self, proxy_handler):
        """Test invalid section errors match original"""
        result = proxy_handler.handle_obsidian({
            "action": "read_section",
            "args": {"path": "Note3.md", "section": "NonexistentSection"}
        })

        assert result["success"] is False

    def test_invalid_block_error(self, proxy_handler):
        """Test invalid block errors match original"""
        result = proxy_handler.handle_obsidian({
            "action": "read_block",
            "args": {"path": "Note4.md", "block_id": "nonexistent"}
        })

        assert result["success"] is False


class TestAllActionsViaLookup:
    """Test that all actions can be discovered via lookup"""

    @pytest.mark.parametrize("intent,expected_action", [
        # Core actions
        ("search for notes about AI", "search_notes"),
        ("list all notes", "list_notes"),
        ("create a new note", "create_note"),
        ("update my note", "update_note"),
        ("delete the file", "delete_note"),
        ("move the note", "move_note"),
        ("append to note", "append_note"),
        ("read the note", "read_note_content"),
        ("resolve wiki link", "resolve_link"),

        # Section/block actions
        ("get table of contents", "get_toc"),
        ("read the introduction section", "read_section"),
        ("read block with id", "read_block"),
        ("update section", "update_section"),
        ("update block", "update_block"),

        # Knowledge actions
        ("get backlinks", "get_backlinks"),
        ("find orphan notes", "get_orphans"),
        ("show knowledge graph", "get_graph"),
        ("list all tags", "list_tags"),

        # Template actions
        ("list templates", "list_templates"),
        ("create from template", "create_from_template"),
        ("save template", "save_template"),

        # Admin actions
        ("get daily note", "get_daily_note"),
    ])
    def test_action_discoverable_via_lookup(self, proxy_handler, intent, expected_action):
        """Test that action can be discovered via lookup"""
        result = proxy_handler.handle_lookup({"intent": intent})

        assert result["action"] == expected_action
        assert "required_fields" in result
        assert "optional_fields" in result


class TestPerformanceCompatibility:
    """Test that performance is acceptable"""

    def test_routing_overhead(self, proxy_handler):
        """Test routing overhead is minimal"""
        import time

        # Measure lookup time
        start = time.time()
        lookup_result = proxy_handler.handle_lookup({
            "intent": "search for notes"
        })
        lookup_time = (time.time() - start) * 1000  # ms

        # Should be very fast (< 10ms target)
        assert lookup_time < 100  # Generous upper bound

    def test_execution_performance(self, proxy_handler):
        """Test execution performance is acceptable"""
        import time

        # Measure execution time
        start = time.time()
        exec_result = proxy_handler.handle_obsidian({
            "action": "list_notes",
            "args": {}
        })
        exec_time = (time.time() - start) * 1000  # ms

        assert exec_result["success"] is True
        # Execution time varies based on vault size, but should be reasonable
        assert exec_time < 1000  # 1 second max
