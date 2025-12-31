"""
Unit tests for action registry and handlers
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from app.mcp.actions import ActionRegistry, ActionExecutionError


@pytest.fixture
def mock_vault_manager():
    """Create a mock VaultManager"""
    vault = Mock()
    vault.vault_path = Path("/test/vault")
    vault.cache = Mock()
    vault.parser = Mock()
    return vault


@pytest.fixture
def action_registry(mock_vault_manager):
    """Create an ActionRegistry with mocked VaultManager"""
    return ActionRegistry(mock_vault_manager)


class TestActionRegistry:
    """Test ActionRegistry initialization and setup"""

    def test_initialization(self, mock_vault_manager):
        """Test ActionRegistry initialization"""
        registry = ActionRegistry(mock_vault_manager)

        assert registry.vault == mock_vault_manager
        assert registry.bundle_manager is not None
        assert registry.router is not None
        assert len(registry._handlers) > 0

    def test_all_actions_registered(self, action_registry):
        """Test all expected actions are registered"""
        actions = action_registry.list_actions()

        # Core actions
        assert "search_notes" in actions
        assert "list_notes" in actions
        assert "create_note" in actions
        assert "update_note" in actions
        assert "delete_note" in actions

        # Knowledge actions
        assert "get_backlinks" in actions
        assert "get_orphans" in actions
        assert "get_graph" in actions

        # Templates actions
        assert "list_templates" in actions
        assert "create_from_template" in actions

        # Admin actions
        assert "health_check" in actions
        assert "get_stats" in actions

    def test_has_action(self, action_registry):
        """Test checking if action exists"""
        assert action_registry.has_action("search_notes") is True
        assert action_registry.has_action("unknown_action") is False


class TestActionExecution:
    """Test action execution with validation"""

    def test_execute_unknown_action(self, action_registry):
        """Test executing unknown action fails"""
        with pytest.raises(ActionExecutionError) as exc_info:
            action_registry.execute_action("unknown_action", {})

        assert "Unknown action" in str(exc_info.value)

    def test_execute_missing_required_fields(self, action_registry):
        """Test executing action with missing required fields fails"""
        with pytest.raises(ActionExecutionError) as exc_info:
            action_registry.execute_action("search_notes", {})

        assert "Invalid arguments" in str(exc_info.value)
        assert "query" in str(exc_info.value)

    def test_execute_with_limit_exceeded(self, action_registry):
        """Test executing action with exceeded limit fails"""
        with pytest.raises(ActionExecutionError) as exc_info:
            action_registry.execute_action(
                "search_notes",
                {"query": "test", "limit": 10000}
            )

        assert "Limit exceeded" in str(exc_info.value)

    def test_execute_success_structure(self, action_registry, mock_vault_manager):
        """Test successful execution returns correct structure"""
        mock_vault_manager.search_notes.return_value = []

        result = action_registry.execute_action(
            "search_notes",
            {"query": "test"}
        )

        assert result["success"] is True
        assert result["action"] == "search_notes"
        assert result["bundle"] == "core"
        assert "result" in result


class TestCoreActionHandlers:
    """Test CORE bundle action handlers"""

    def test_search_notes(self, action_registry, mock_vault_manager):
        """Test search_notes handler"""
        mock_vault_manager.search_notes.return_value = [
            {"title": "Note 1", "path": "note1.md"},
            {"title": "Note 2", "path": "note2.md"}
        ]

        result = action_registry.execute_action(
            "search_notes",
            {"query": "test", "limit": 10}
        )

        assert result["success"] is True
        assert result["result"]["count"] == 2
        assert len(result["result"]["results"]) == 2

        # Verify VaultManager was called correctly
        mock_vault_manager.search_notes.assert_called_once_with(
            query="test",
            tags=None,
            limit=10,
            use_regex=False
        )

    def test_list_notes(self, action_registry, mock_vault_manager):
        """Test list_notes handler"""
        mock_vault_manager.list_notes.return_value = [
            {"name": "Note 1", "path": "note1.md", "tags": ["tag1"]},
            {"name": "Note 2", "path": "note2.md", "tags": ["tag2"]}
        ]

        result = action_registry.execute_action(
            "list_notes",
            {"limit": 50}
        )

        assert result["success"] is True
        assert result["result"]["count"] == 2

        mock_vault_manager.list_notes.assert_called_once()

    def test_get_note_metadata_only(self, action_registry, mock_vault_manager):
        """Test get_note handler (metadata only)"""
        mock_vault_manager.get_note_metadata.return_value = {
            "name": "Test Note",
            "path": "test.md",
            "tags": []
        }

        result = action_registry.execute_action(
            "get_note",
            {"title": "Test Note"}
        )

        assert result["success"] is True
        assert "content" not in result["result"]
        mock_vault_manager.get_note_metadata.assert_called_once()

    def test_get_note_with_content(self, action_registry, mock_vault_manager):
        """Test get_note handler with content"""
        mock_vault_manager.get_note_metadata.return_value = {
            "name": "Test Note",
            "path": "test.md"
        }
        mock_vault_manager.parser.resolve_wiki_link.return_value = "test.md"
        mock_vault_manager.read_note.return_value = {
            "content": "Note content"
        }

        result = action_registry.execute_action(
            "get_note",
            {"title": "Test Note", "include_content": True}
        )

        assert result["success"] is True
        assert result["result"]["content"] == "Note content"

    def test_read_note_content(self, action_registry, mock_vault_manager):
        """Test read_note_content handler"""
        mock_vault_manager.parser.resolve_wiki_link.return_value = "test.md"
        mock_vault_manager.read_note.return_value = {
            "name": "Test",
            "content": "Full content"
        }

        result = action_registry.execute_action(
            "read_note_content",
            {"title": "Test"}
        )

        assert result["success"] is True
        assert result["result"]["content"] == "Full content"

    def test_create_note(self, action_registry, mock_vault_manager):
        """Test create_note handler"""
        mock_vault_manager.create_note.return_value = {
            "path": "new-note.md",
            "tags": ["tag1"]
        }

        result = action_registry.execute_action(
            "create_note",
            {"title": "New Note", "content": "Content", "tags": ["tag1"]}
        )

        assert result["success"] is True
        assert result["result"]["path"] == "new-note.md"

        # Verify frontmatter includes tags
        call_args = mock_vault_manager.create_note.call_args
        assert call_args[0][2]["tags"] == ["tag1"]

    def test_update_note(self, action_registry, mock_vault_manager):
        """Test update_note handler"""
        mock_vault_manager.update_note.return_value = {
            "path": "test.md",
            "modified": "2024-01-01"
        }

        result = action_registry.execute_action(
            "update_note",
            {"file_path": "test.md", "content": "New content"}
        )

        assert result["success"] is True
        mock_vault_manager.update_note.assert_called_once()

    def test_append_note(self, action_registry, mock_vault_manager):
        """Test append_note handler"""
        mock_vault_manager.update_note.return_value = {"path": "test.md"}

        result = action_registry.execute_action(
            "append_note",
            {"file_path": "test.md", "content": "Appended"}
        )

        assert result["success"] is True

        # Verify append=True was passed
        call_args = mock_vault_manager.update_note.call_args
        assert call_args[1]["append"] is True

    def test_delete_note(self, action_registry, mock_vault_manager):
        """Test delete_note handler"""
        result = action_registry.execute_action(
            "delete_note",
            {"file_path": "test.md"}
        )

        assert result["success"] is True
        assert result["result"]["deleted"] == "test.md"
        mock_vault_manager.delete_note.assert_called_once_with("test.md")

    def test_move_note(self, action_registry, mock_vault_manager):
        """Test move_note handler"""
        mock_vault_manager.move_note.return_value = {
            "path": "new-path.md"
        }

        result = action_registry.execute_action(
            "move_note",
            {"old_path": "old.md", "new_path": "new-path.md"}
        )

        assert result["success"] is True
        mock_vault_manager.move_note.assert_called_once()

    def test_resolve_link(self, action_registry, mock_vault_manager):
        """Test resolve_link handler"""
        mock_vault_manager.parser.resolve_wiki_link.return_value = "notes/test.md"

        result = action_registry.execute_action(
            "resolve_link",
            {"link_name": "Test Note"}
        )

        assert result["success"] is True
        assert result["result"]["resolved"] is True
        assert result["result"]["path"] == "notes/test.md"

    def test_get_toc(self, action_registry, mock_vault_manager):
        """Test get_toc handler"""
        mock_vault_manager.get_table_of_contents.return_value = {
            "toc": [],
            "heading_count": 0
        }

        result = action_registry.execute_action(
            "get_toc",
            {"path": "test.md"}
        )

        assert result["success"] is True
        mock_vault_manager.get_table_of_contents.assert_called_once()

    def test_read_section(self, action_registry, mock_vault_manager):
        """Test read_section handler"""
        mock_vault_manager.read_section.return_value = {
            "heading_text": "Introduction",
            "content": "Section content"
        }

        result = action_registry.execute_action(
            "read_section",
            {"path": "test.md", "section": "Introduction"}
        )

        assert result["success"] is True
        assert result["result"]["content"] == "Section content"

    def test_update_section(self, action_registry, mock_vault_manager):
        """Test update_section handler"""
        mock_vault_manager.update_section.return_value = {"size": 1000}

        result = action_registry.execute_action(
            "update_section",
            {"path": "test.md", "section": "Intro", "content": "New"}
        )

        assert result["success"] is True
        mock_vault_manager.update_section.assert_called_once()


class TestKnowledgeActionHandlers:
    """Test KNOWLEDGE bundle action handlers"""

    def test_get_backlinks(self, action_registry, mock_vault_manager):
        """Test get_backlinks handler"""
        mock_vault_manager.get_backlinks.return_value = {
            "backlink_count": 2,
            "backlinks": []
        }

        result = action_registry.execute_action(
            "get_backlinks",
            {"title": "Test Note"}
        )

        assert result["success"] is True
        assert result["result"]["backlink_count"] == 2

    def test_get_orphans(self, action_registry, mock_vault_manager):
        """Test get_orphans handler"""
        mock_vault_manager.get_orphan_notes.return_value = [
            {"name": "Orphan 1"},
            {"name": "Orphan 2"}
        ]

        result = action_registry.execute_action(
            "get_orphans",
            {"limit": 100}
        )

        assert result["success"] is True
        assert result["result"]["count"] == 2

    def test_get_graph(self, action_registry, mock_vault_manager):
        """Test get_graph handler"""
        mock_vault_manager.get_note_graph.return_value = {
            "node_count": 10,
            "edge_count": 15
        }

        result = action_registry.execute_action(
            "get_graph",
            {"depth": 2, "max_nodes": 50}
        )

        assert result["success"] is True
        assert result["result"]["node_count"] == 10

    def test_list_tags(self, action_registry, mock_vault_manager):
        """Test list_tags handler"""
        mock_vault_manager.list_notes.return_value = [
            {"tags": ["ai", "ml"]},
            {"tags": ["ai", "python"]},
            {"tags": []}
        ]

        result = action_registry.execute_action("list_tags", {})

        assert result["success"] is True
        tags = result["result"]["tags"]
        assert len(tags) == 3  # ai, ml, python

        # Verify counts
        ai_tag = next(t for t in tags if t["tag"] == "ai")
        assert ai_tag["count"] == 2


class TestTemplatesActionHandlers:
    """Test TEMPLATES bundle action handlers"""

    def test_list_templates(self, action_registry, mock_vault_manager):
        """Test list_templates handler"""
        mock_vault_manager.list_templates.return_value = {
            "count": 2,
            "templates": []
        }

        result = action_registry.execute_action("list_templates", {})

        assert result["success"] is True
        assert result["result"]["count"] == 2

    def test_create_from_template(self, action_registry, mock_vault_manager):
        """Test create_from_template handler"""
        mock_vault_manager.create_from_template.return_value = {
            "size": 500
        }

        result = action_registry.execute_action(
            "create_from_template",
            {
                "template_name": "meeting",
                "note_path": "meetings/2024-01-01.md",
                "variables": {"title": "Team Meeting"}
            }
        )

        assert result["success"] is True
        mock_vault_manager.create_from_template.assert_called_once()

    def test_save_template(self, action_registry, mock_vault_manager):
        """Test save_template handler"""
        mock_vault_manager.save_template.return_value = {
            "name": "my-template"
        }

        result = action_registry.execute_action(
            "save_template",
            {"template_name": "my-template", "content": "# {{title}}"}
        )

        assert result["success"] is True
        mock_vault_manager.save_template.assert_called_once()


class TestAdminActionHandlers:
    """Test ADMIN bundle action handlers"""

    def test_health_check_healthy(self, action_registry, mock_vault_manager):
        """Test health_check handler when healthy"""
        mock_vault_manager.vault_path = Path("/test/vault")
        mock_vault_manager.vault_path.exists = Mock(return_value=True)
        mock_vault_manager.vault_path.is_dir = Mock(return_value=True)
        mock_vault_manager.vault_path.rglob = Mock(return_value=[
            Path("note1.md"),
            Path("note2.md")
        ])

        result = action_registry.execute_action("health_check", {})

        assert result["success"] is True
        assert result["result"]["healthy"] is True
        assert result["result"]["notes_count"] == 2

    def test_get_stats(self, action_registry, mock_vault_manager):
        """Test get_stats handler"""
        mock_vault_manager.get_vault_stats.return_value = {
            "total_notes": 100,
            "total_size": 50000
        }

        result = action_registry.execute_action("get_stats", {})

        assert result["success"] is True
        assert result["result"]["total_notes"] == 100

    def test_clear_cache(self, action_registry, mock_vault_manager):
        """Test clear_cache handler"""
        result = action_registry.execute_action("clear_cache", {})

        assert result["success"] is True
        mock_vault_manager.cache.clear.assert_called_once()

    def test_clear_cache_with_pattern(self, action_registry, mock_vault_manager):
        """Test clear_cache handler with pattern"""
        mock_vault_manager.cache.delete_pattern.return_value = 5

        result = action_registry.execute_action(
            "clear_cache",
            {"pattern": "note:*"}
        )

        assert result["success"] is True
        mock_vault_manager.cache.delete_pattern.assert_called_once_with("note:*")

    def test_get_daily_note(self, action_registry, mock_vault_manager):
        """Test get_daily_note handler"""
        mock_vault_manager.get_daily_note.return_value = {
            "name": "2024-01-01",
            "content": "Daily note"
        }

        result = action_registry.execute_action(
            "get_daily_note",
            {"date": "2024-01-01"}
        )

        assert result["success"] is True
        mock_vault_manager.get_daily_note.assert_called_once_with("2024-01-01")


class TestErrorHandling:
    """Test error handling in action execution"""

    def test_vault_manager_exception(self, action_registry, mock_vault_manager):
        """Test handling of VaultManager exceptions"""
        mock_vault_manager.search_notes.side_effect = Exception("Vault error")

        with pytest.raises(ActionExecutionError) as exc_info:
            action_registry.execute_action(
                "search_notes",
                {"query": "test"}
            )

        assert "Action failed" in str(exc_info.value)
        assert "Vault error" in str(exc_info.value)

    def test_file_not_found_exception(self, action_registry, mock_vault_manager):
        """Test handling of FileNotFoundError"""
        mock_vault_manager.read_section.side_effect = FileNotFoundError("Not found")

        with pytest.raises(ActionExecutionError):
            action_registry.execute_action(
                "read_section",
                {"path": "missing.md", "section": "Intro"}
            )

    def test_value_error_exception(self, action_registry, mock_vault_manager):
        """Test handling of ValueError"""
        mock_vault_manager.update_section.side_effect = ValueError("Invalid section")

        with pytest.raises(ActionExecutionError):
            action_registry.execute_action(
                "update_section",
                {"path": "test.md", "section": "Unknown", "content": "New"}
            )
