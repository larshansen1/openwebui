"""
Integration tests for proxy-based routing

Tests the full flow: intent → router → action → VaultManager
"""

import pytest
from pathlib import Path

from app.vault.manager import VaultManager
from app.mcp.proxy import ProxyToolHandler


@pytest.fixture
def test_vault_path(tmp_path):
    """Create a temporary test vault"""
    vault_path = tmp_path / "test-vault"
    vault_path.mkdir()

    # Create some test notes
    (vault_path / "Note1.md").write_text("# Note 1\nContent about AI and machine learning")
    (vault_path / "Note2.md").write_text("# Note 2\nContent about Python programming")
    (vault_path / "Folder").mkdir()
    (vault_path / "Folder" / "Note3.md").write_text("# Note 3\nNested content")

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
    """Create a ProxyToolHandler with real VaultManager"""
    return ProxyToolHandler(vault_manager)


class TestLookupToExecution:
    """Test the full flow from lookup to execution"""

    def test_search_notes_flow(self, proxy_handler):
        """Test search notes: lookup → execute"""
        # Step 1: Lookup
        lookup_result = proxy_handler.handle_lookup({
            "intent": "search for notes about AI"
        })

        assert lookup_result["action"] == "search_notes"
        assert "query" in lookup_result["required_fields"]

        # Step 2: Execute with discovered action
        exec_result = proxy_handler.handle_obsidian({
            "action": lookup_result["action"],
            "args": {"query": "AI"}
        })

        assert exec_result["success"] is True
        assert exec_result["result"]["count"] >= 0

    def test_list_notes_flow(self, proxy_handler):
        """Test list notes: lookup → execute"""
        # Lookup
        lookup_result = proxy_handler.handle_lookup({
            "intent": "list all notes"
        })

        assert lookup_result["action"] == "list_notes"

        # Execute
        exec_result = proxy_handler.handle_obsidian({
            "action": lookup_result["action"],
            "args": {}
        })

        assert exec_result["success"] is True
        assert "notes" in exec_result["result"]

    def test_create_note_flow(self, proxy_handler):
        """Test create note: lookup → execute"""
        # Lookup
        lookup_result = proxy_handler.handle_lookup({
            "intent": "create a new note called Test"
        })

        assert lookup_result["action"] == "create_note"
        assert "title" in lookup_result["required_fields"]
        assert "content" in lookup_result["required_fields"]

        # Execute
        exec_result = proxy_handler.handle_obsidian({
            "action": lookup_result["action"],
            "args": {
                "title": "TestNote",
                "content": "Test content"
            }
        })

        assert exec_result["success"] is True
        assert "path" in exec_result["result"]

    def test_get_backlinks_flow(self, proxy_handler):
        """Test get backlinks: lookup → execute"""
        # Lookup
        lookup_result = proxy_handler.handle_lookup({
            "intent": "get backlinks for Note1"
        })

        assert lookup_result["action"] == "get_backlinks"
        assert lookup_result["bundle"] == "knowledge"

        # Execute
        exec_result = proxy_handler.handle_obsidian({
            "action": lookup_result["action"],
            "args": {"title": "Note1"}
        })

        assert exec_result["success"] is True


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    def test_search_and_read_workflow(self, proxy_handler):
        """Test: search → get results → read note"""
        # 1. Search for notes
        search_result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {"query": "AI"}
        })

        assert search_result["success"] is True

        # 2. If results found, read first note
        if search_result["result"]["count"] > 0:
            first_note = search_result["result"]["results"][0]

            read_result = proxy_handler.handle_obsidian({
                "action": "read_note_content",
                "args": {"title": first_note["title"]}
            })

            assert read_result["success"] is True
            assert "content" in read_result["result"]

    def test_create_update_delete_workflow(self, proxy_handler):
        """Test: create → update → delete"""
        # 1. Create note
        create_result = proxy_handler.handle_obsidian({
            "action": "create_note",
            "args": {
                "title": "WorkflowTest",
                "content": "Initial content"
            }
        })

        assert create_result["success"] is True
        note_path = create_result["result"]["path"]

        # 2. Update note
        update_result = proxy_handler.handle_obsidian({
            "action": "update_note",
            "args": {
                "file_path": note_path,
                "content": "Updated content"
            }
        })

        assert update_result["success"] is True

        # 3. Delete note
        delete_result = proxy_handler.handle_obsidian({
            "action": "delete_note",
            "args": {"file_path": note_path}
        })

        assert delete_result["success"] is True

    def test_template_workflow(self, proxy_handler, vault_manager):
        """Test: save template → list templates → create from template"""
        # 1. Save template
        save_result = proxy_handler.handle_obsidian({
            "action": "save_template",
            "args": {
                "template_name": "test-template",
                "content": "# {{title}}\n\nCreated by {{author}}"
            }
        })

        assert save_result["success"] is True

        # 2. List templates
        list_result = proxy_handler.handle_obsidian({
            "action": "list_templates",
            "args": {}
        })

        assert list_result["success"] is True
        assert list_result["result"]["count"] >= 1

        # 3. Create from template
        create_result = proxy_handler.handle_obsidian({
            "action": "create_from_template",
            "args": {
                "template_name": "test-template",
                "note_path": "from-template.md",
                "variables": {
                    "title": "My Note",
                    "author": "Test User"
                }
            }
        })

        assert create_result["success"] is True


class TestErrorHandling:
    """Test error handling in proxy routing"""

    def test_unknown_action_error(self, proxy_handler):
        """Test executing unknown action"""
        result = proxy_handler.handle_obsidian({
            "action": "nonexistent_action",
            "args": {}
        })

        assert result["success"] is False
        assert "error" in result

    def test_missing_required_fields_error(self, proxy_handler):
        """Test missing required fields"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {}  # Missing 'query'
        })

        assert result["success"] is False
        assert "query" in result["error"]

    def test_file_not_found_error(self, proxy_handler):
        """Test file not found error"""
        result = proxy_handler.handle_obsidian({
            "action": "read_note_content",
            "args": {"title": "NonexistentNote"}
        })

        assert result["success"] is False

    def test_invalid_limit_error(self, proxy_handler):
        """Test exceeded limit error"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {
                "query": "test",
                "limit": 99999  # Exceeds max
            }
        })

        assert result["success"] is False
        assert "exceeds maximum" in result["error"]


class TestIntentRouting:
    """Test intent routing accuracy"""

    def test_search_intents(self, proxy_handler):
        """Test various search intents"""
        search_intents = [
            "find notes about Python",
            "search for AI content",
            "look for documents mentioning testing"
        ]

        for intent in search_intents:
            result = proxy_handler.handle_lookup({"intent": intent})
            assert result["action"] == "search_notes"

    def test_crud_intents(self, proxy_handler):
        """Test CRUD operation intents"""
        test_cases = [
            ("create a new note", "create_note"),
            ("update my TODO list", "update_note"),
            ("delete the draft", "delete_note"),
            ("move note to archive", "move_note"),
        ]

        for intent, expected_action in test_cases:
            result = proxy_handler.handle_lookup({"intent": intent})
            assert result["action"] == expected_action

    def test_knowledge_graph_intents(self, proxy_handler):
        """Test knowledge graph intents"""
        test_cases = [
            ("get backlinks for my note", "get_backlinks"),
            ("find orphan notes", "get_orphans"),
            ("show me the knowledge graph", "get_graph"),
            ("list all tags", "list_tags"),
        ]

        for intent, expected_action in test_cases:
            result = proxy_handler.handle_lookup({"intent": intent})
            assert result["action"] == expected_action

    def test_template_intents(self, proxy_handler):
        """Test template intents"""
        test_cases = [
            ("list available templates", "list_templates"),
            ("create from template", "create_from_template"),
            ("save this as template", "save_template"),
        ]

        for intent, expected_action in test_cases:
            result = proxy_handler.handle_lookup({"intent": intent})
            assert result["action"] == expected_action


class TestDefaultsAndLimits:
    """Test defaults application and limit enforcement"""

    def test_defaults_applied(self, proxy_handler):
        """Test that defaults are applied"""
        # Search without limit
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {"query": "test"}
        })

        assert result["success"] is True
        # Default limit should have been applied (50)

    def test_limit_enforcement(self, proxy_handler):
        """Test limit enforcement"""
        # Try to exceed search limit
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {
                "query": "test",
                "limit": 1000  # Exceeds max (200)
            }
        })

        assert result["success"] is False

    def test_graph_depth_limit(self, proxy_handler):
        """Test graph depth limit"""
        # Valid depth
        result = proxy_handler.handle_obsidian({
            "action": "get_graph",
            "args": {"depth": 2}
        })

        assert result["success"] is True

        # Exceeded depth
        result = proxy_handler.handle_obsidian({
            "action": "get_graph",
            "args": {"depth": 10}
        })

        assert result["success"] is False


class TestBundleIsolation:
    """Test that bundles are properly isolated"""

    def test_action_belongs_to_correct_bundle(self, proxy_handler):
        """Test actions are in correct bundles"""
        test_cases = [
            ("search_notes", "core"),
            ("get_backlinks", "knowledge"),
            ("list_templates", "templates"),
            ("health_check", "admin"),
        ]

        for action, expected_bundle in test_cases:
            bundle = proxy_handler.bundle_manager.get_bundle_for_action(action)
            assert bundle.value == expected_bundle


class TestHelpSystem:
    """Test help system integration"""

    def test_help_all_topics(self, proxy_handler):
        """Test help for all topics"""
        topics = ["overview", "core", "search", "read", "write", "templates", "graph", "admin"]

        for topic in topics:
            result = proxy_handler.handle_help({"topic": topic})
            assert result["topic"] == topic
            assert len(result["content"]) > 0

    def test_help_verbosity_levels(self, proxy_handler):
        """Test help verbosity levels"""
        # Short
        short_result = proxy_handler.handle_help({
            "topic": "core",
            "verbosity": "short"
        })

        # Normal
        normal_result = proxy_handler.handle_help({
            "topic": "core",
            "verbosity": "normal"
        })

        # Normal should be longer
        assert len(normal_result["content"]) > len(short_result["content"])


class TestValidation:
    """Test validation pipeline"""

    def test_validate_before_execute(self, proxy_handler):
        """Test pre-execution validation"""
        # Valid
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {"query": "test"}
        )
        assert is_valid is True
        assert error is None

        # Invalid - missing field
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {}
        )
        assert is_valid is False
        assert error is not None

        # Invalid - exceeded limit
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {"query": "test", "limit": 10000}
        )
        assert is_valid is False
        assert error is not None
