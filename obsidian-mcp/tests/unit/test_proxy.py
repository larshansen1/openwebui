"""
Unit tests for proxy tool handlers
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

from app.mcp.proxy import ProxyToolHandler, ProxyToolFormatter
from app.mcp.actions import ActionExecutionError


@pytest.fixture
def mock_vault_manager():
    """Create a mock VaultManager"""
    vault = Mock()
    vault.vault_path = Path("/test/vault")
    vault.cache = Mock()
    vault.parser = Mock()
    return vault


@pytest.fixture
def proxy_handler(mock_vault_manager):
    """Create a ProxyToolHandler with mocked VaultManager"""
    return ProxyToolHandler(mock_vault_manager)


class TestProxyToolHandler:
    """Test ProxyToolHandler initialization and setup"""

    def test_initialization(self, mock_vault_manager):
        """Test ProxyToolHandler initialization"""
        handler = ProxyToolHandler(mock_vault_manager)

        assert handler.vault == mock_vault_manager
        assert handler.router is not None
        assert handler.bundle_manager is not None
        assert handler.action_registry is not None

    def test_suggest_action(self, proxy_handler):
        """Test suggesting action from intent"""
        # Valid intent
        action = proxy_handler.suggest_action("search for notes about AI")
        assert action == "search_notes"

        # Another valid intent
        action = proxy_handler.suggest_action("get backlinks for my note")
        assert action == "get_backlinks"

    def test_list_available_actions(self, proxy_handler):
        """Test listing all available actions"""
        actions = proxy_handler.list_available_actions()

        assert len(actions) > 0
        assert "search_notes" in actions
        assert "get_backlinks" in actions
        assert "list_templates" in actions

    def test_list_available_actions_filtered(self, proxy_handler):
        """Test listing actions filtered by bundle"""
        core_actions = proxy_handler.list_available_actions("core")

        assert len(core_actions) > 0
        assert "search_notes" in core_actions
        assert "create_note" in core_actions

        # Actions from other bundles should not be included
        assert "get_backlinks" not in core_actions

    def test_list_available_actions_invalid_bundle(self, proxy_handler):
        """Test listing actions with invalid bundle filter"""
        actions = proxy_handler.list_available_actions("invalid_bundle")
        assert actions == []

    def test_get_action_details(self, proxy_handler):
        """Test getting action details"""
        details = proxy_handler.get_action_details("search_notes")

        assert details is not None
        assert details["name"] == "search_notes"
        assert details["bundle"] == "core"
        assert "required_fields" in details
        assert "optional_fields" in details

    def test_get_action_details_unknown(self, proxy_handler):
        """Test getting details for unknown action"""
        details = proxy_handler.get_action_details("unknown_action")
        assert details is None

    def test_validate_before_execute(self, proxy_handler):
        """Test validation before execution"""
        # Valid action and args
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {"query": "test"}
        )
        assert is_valid is True
        assert error is None

    def test_validate_before_execute_unknown_action(self, proxy_handler):
        """Test validation with unknown action"""
        is_valid, error = proxy_handler.validate_before_execute(
            "unknown_action",
            {}
        )
        assert is_valid is False
        assert "Unknown action" in error

    def test_validate_before_execute_missing_field(self, proxy_handler):
        """Test validation with missing required field"""
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {}
        )
        assert is_valid is False
        assert "query" in error

    def test_validate_before_execute_limit_exceeded(self, proxy_handler):
        """Test validation with exceeded limit"""
        is_valid, error = proxy_handler.validate_before_execute(
            "search_notes",
            {"query": "test", "limit": 10000}
        )
        assert is_valid is False
        assert "exceeds maximum" in error


class TestHandleLookup:
    """Test handle_lookup functionality"""

    def test_lookup_success(self, proxy_handler):
        """Test successful lookup"""
        result = proxy_handler.handle_lookup({
            "intent": "search for notes about AI"
        })

        assert "bundle" in result
        assert "action" in result
        assert result["action"] == "search_notes"
        assert "required_fields" in result
        assert "optional_fields" in result
        assert "defaults" in result
        assert "limits" in result
        assert "confidence" in result
        assert "reasoning" in result

    def test_lookup_with_note_hint(self, proxy_handler):
        """Test lookup with note hint"""
        result = proxy_handler.handle_lookup({
            "intent": "search for Python",
            "note_hint": "Project Plan"
        })

        assert result["action"] == "search_notes"
        assert "Project Plan" in result["reasoning"]

    def test_lookup_missing_intent(self, proxy_handler):
        """Test lookup with missing intent"""
        result = proxy_handler.handle_lookup({})

        assert "error" in result
        assert "intent" in result["error"]

    def test_lookup_various_intents(self, proxy_handler):
        """Test lookup with various intents"""
        test_cases = [
            ("create a new note", "create_note"),
            ("get backlinks", "get_backlinks"),
            ("list all templates", "list_templates"),
            ("show me the graph", "get_graph"),
        ]

        for intent, expected_action in test_cases:
            result = proxy_handler.handle_lookup({"intent": intent})
            assert result["action"] == expected_action


class TestHandleObsidian:
    """Test handle_obsidian functionality"""

    def test_execute_success(self, proxy_handler, mock_vault_manager):
        """Test successful execution"""
        mock_vault_manager.search_notes.return_value = []

        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {"query": "test"}
        })

        assert result["success"] is True
        assert result["action"] == "search_notes"
        assert result["bundle"] == "core"
        assert "result" in result

    def test_execute_missing_action(self, proxy_handler):
        """Test execution with missing action"""
        result = proxy_handler.handle_obsidian({
            "args": {"query": "test"}
        })

        assert result["success"] is False
        assert "error" in result
        assert "action" in result["error"]

    def test_execute_invalid_args_type(self, proxy_handler):
        """Test execution with invalid args type"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": "not an object"
        })

        assert result["success"] is False
        assert "Invalid 'args'" in result["error"]

    def test_execute_unknown_action(self, proxy_handler):
        """Test execution with unknown action"""
        result = proxy_handler.handle_obsidian({
            "action": "unknown_action",
            "args": {}
        })

        assert result["success"] is False
        assert "error" in result

    def test_execute_missing_required_field(self, proxy_handler):
        """Test execution with missing required field"""
        result = proxy_handler.handle_obsidian({
            "action": "search_notes",
            "args": {}
        })

        assert result["success"] is False
        assert "error" in result

    def test_execute_various_actions(self, proxy_handler, mock_vault_manager):
        """Test executing various actions"""
        # Mock return values
        mock_vault_manager.search_notes.return_value = []
        mock_vault_manager.list_notes.return_value = []
        mock_vault_manager.get_backlinks.return_value = {"backlink_count": 0}

        test_cases = [
            ("search_notes", {"query": "test"}),
            ("list_notes", {}),
            ("get_backlinks", {"title": "Test"}),
        ]

        for action, args in test_cases:
            result = proxy_handler.handle_obsidian({
                "action": action,
                "args": args
            })
            assert result["success"] is True


class TestHandleHelp:
    """Test handle_help functionality"""

    def test_help_default(self, proxy_handler):
        """Test help with no arguments"""
        result = proxy_handler.handle_help({})

        assert "topic" in result
        assert "verbosity" in result
        assert "content" in result
        assert "available_topics" in result
        assert result["topic"] == "overview"
        assert result["verbosity"] == "short"

    def test_help_specific_topic(self, proxy_handler):
        """Test help with specific topic"""
        result = proxy_handler.handle_help({
            "topic": "core"
        })

        assert result["topic"] == "core"
        assert "core" in result["content"].lower()

    def test_help_normal_verbosity(self, proxy_handler):
        """Test help with normal verbosity"""
        result = proxy_handler.handle_help({
            "verbosity": "normal"
        })

        assert result["verbosity"] == "normal"
        assert len(result["content"]) > 100  # Should be more verbose

    def test_help_invalid_verbosity(self, proxy_handler):
        """Test help with invalid verbosity falls back to short"""
        result = proxy_handler.handle_help({
            "verbosity": "invalid"
        })

        assert result["verbosity"] == "short"

    def test_help_all_topics(self, proxy_handler):
        """Test help for all topics"""
        topics = ["overview", "core", "search", "read", "write", "templates", "graph", "admin"]

        for topic in topics:
            result = proxy_handler.handle_help({"topic": topic})
            assert result["topic"] == topic
            assert len(result["content"]) > 0


class TestProxyToolFormatter:
    """Test ProxyToolFormatter functionality"""

    def test_format_lookup_result_success(self):
        """Test formatting successful lookup result"""
        result = {
            "bundle": "core",
            "action": "search_notes",
            "required_fields": ["query"],
            "optional_fields": ["limit", "tags"],
            "defaults": {"limit": 50},
            "limits": {"max_limit": 200},
            "confidence": 0.8,
            "reasoning": "Intent matched pattern",
            "description": "Search for notes",
            "field_descriptions": {
                "query": "Search query",
                "limit": "Maximum results"
            }
        }

        text = ProxyToolFormatter.format_lookup_result(result)

        assert "search_notes" in text
        assert "core" in text
        assert "80%" in text  # Confidence
        assert "query" in text
        assert "limit" in text

    def test_format_lookup_result_error(self):
        """Test formatting lookup error"""
        result = {
            "error": "Missing intent",
            "usage": "Provide intent"
        }

        text = ProxyToolFormatter.format_lookup_result(result)

        assert "Error" in text
        assert "Missing intent" in text

    def test_format_execution_result_success(self):
        """Test formatting successful execution result"""
        result = {
            "success": True,
            "action": "search_notes",
            "bundle": "core",
            "result": {
                "count": 5,
                "results": []
            }
        }

        text = ProxyToolFormatter.format_execution_result(result)

        assert "search_notes" in text
        assert "core" in text
        assert "5 results" in text

    def test_format_execution_result_failure(self):
        """Test formatting execution failure"""
        result = {
            "success": False,
            "action": "search_notes",
            "bundle": "core",
            "error": "Query failed"
        }

        text = ProxyToolFormatter.format_execution_result(result)

        assert "Failed" in text
        assert "search_notes" in text
        assert "Query failed" in text

    def test_format_execution_result_content(self):
        """Test formatting execution result with content"""
        result = {
            "success": True,
            "action": "read_note_content",
            "bundle": "core",
            "result": {
                "content": "Note content here"
            }
        }

        text = ProxyToolFormatter.format_execution_result(result)

        assert "Note content here" in text

    def test_format_help_result(self):
        """Test formatting help result"""
        result = {
            "topic": "core",
            "verbosity": "short",
            "content": "Core operations help text",
            "available_topics": ["overview", "core", "search"]
        }

        text = ProxyToolFormatter.format_help_result(result)

        assert "core" in text
        assert "Core operations help text" in text
        assert "overview" in text
        assert "short" in text
