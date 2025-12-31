"""
Unit tests for bundle definitions and management
"""

import pytest
from app.mcp.bundles import (
    Bundle,
    ActionDefinition,
    BundleConfig,
    BundleDefinitions,
    BundleManager
)


class TestActionDefinition:
    """Test ActionDefinition dataclass"""

    def test_action_definition_creation(self):
        """Test creating an action definition"""
        action = ActionDefinition(
            name="test_action",
            bundle=Bundle.CORE,
            description="Test action",
            required_fields=["field1"],
            optional_fields=["field2"],
            defaults={"field2": "default"},
            field_descriptions={"field1": "Required field"}
        )

        assert action.name == "test_action"
        assert action.bundle == Bundle.CORE
        assert action.description == "Test action"
        assert "field1" in action.required_fields
        assert "field2" in action.optional_fields
        assert action.defaults["field2"] == "default"

    def test_action_to_dict(self):
        """Test converting action to dictionary"""
        action = ActionDefinition(
            name="test_action",
            bundle=Bundle.CORE,
            description="Test",
            required_fields=["field1"],
            optional_fields=["field2"],
            defaults={"field2": "val"}
        )

        result = action.to_dict()

        assert result["name"] == "test_action"
        assert result["bundle"] == "core"
        assert result["description"] == "Test"
        assert result["required_fields"] == ["field1"]
        assert result["optional_fields"] == ["field2"]
        assert result["defaults"] == {"field2": "val"}


class TestBundleDefinitions:
    """Test BundleDefinitions registry"""

    def test_get_all_actions(self):
        """Test getting all action definitions"""
        actions = BundleDefinitions.get_all_actions()

        assert len(actions) > 0
        assert all(isinstance(a, ActionDefinition) for a in actions)

        # Check we have actions from different bundles
        bundles = {a.bundle for a in actions}
        assert Bundle.CORE in bundles
        assert Bundle.KNOWLEDGE in bundles
        assert Bundle.TEMPLATES in bundles
        assert Bundle.ADMIN in bundles

    def test_get_action_by_name(self):
        """Test getting action by name"""
        # Test existing action
        action = BundleDefinitions.get_action("search_notes")
        assert action is not None
        assert action.name == "search_notes"
        assert action.bundle == Bundle.CORE

        # Test non-existent action
        action = BundleDefinitions.get_action("nonexistent")
        assert action is None

    def test_get_bundle_actions(self):
        """Test getting all actions for a bundle"""
        core_actions = BundleDefinitions.get_bundle_actions(Bundle.CORE)

        assert len(core_actions) > 0
        assert all(a.bundle == Bundle.CORE for a in core_actions)

        # Check expected actions
        action_names = [a.name for a in core_actions]
        assert "search_notes" in action_names
        assert "create_note" in action_names
        assert "read_section" in action_names

    def test_get_bundle_config(self):
        """Test getting bundle configuration"""
        config = BundleDefinitions.get_bundle_config(Bundle.CORE)

        assert config is not None
        assert config.bundle == Bundle.CORE
        assert len(config.actions) > 0
        assert isinstance(config.limits, dict)
        assert isinstance(config.defaults, dict)

    def test_core_bundle_actions(self):
        """Test CORE bundle has expected actions"""
        actions = BundleDefinitions.CORE_ACTIONS
        action_names = [a.name for a in actions]

        # Search and list
        assert "search_notes" in action_names
        assert "list_notes" in action_names

        # CRUD operations
        assert "create_note" in action_names
        assert "update_note" in action_names
        assert "delete_note" in action_names
        assert "move_note" in action_names

        # Section/block operations
        assert "get_toc" in action_names
        assert "read_section" in action_names
        assert "update_section" in action_names
        assert "read_block" in action_names
        assert "update_block" in action_names

    def test_knowledge_bundle_actions(self):
        """Test KNOWLEDGE bundle has expected actions"""
        actions = BundleDefinitions.KNOWLEDGE_ACTIONS
        action_names = [a.name for a in actions]

        assert "get_backlinks" in action_names
        assert "get_orphans" in action_names
        assert "get_graph" in action_names
        assert "list_tags" in action_names

    def test_templates_bundle_actions(self):
        """Test TEMPLATES bundle has expected actions"""
        actions = BundleDefinitions.TEMPLATES_ACTIONS
        action_names = [a.name for a in actions]

        assert "list_templates" in action_names
        assert "create_from_template" in action_names
        assert "save_template" in action_names
        assert "delete_template" in action_names

    def test_admin_bundle_actions(self):
        """Test ADMIN bundle has expected actions"""
        actions = BundleDefinitions.ADMIN_ACTIONS
        action_names = [a.name for a in actions]

        assert "health_check" in action_names
        assert "get_stats" in action_names
        assert "clear_cache" in action_names
        assert "get_daily_note" in action_names


class TestBundleManager:
    """Test BundleManager functionality"""

    def test_initialization(self):
        """Test BundleManager initialization"""
        manager = BundleManager()

        # Should index all actions
        all_actions = BundleDefinitions.get_all_actions()
        assert len(manager._action_to_bundle) == len(all_actions)

    def test_get_bundle_for_action(self):
        """Test getting bundle for action"""
        manager = BundleManager()

        # Test known actions
        assert manager.get_bundle_for_action("search_notes") == Bundle.CORE
        assert manager.get_bundle_for_action("get_backlinks") == Bundle.KNOWLEDGE
        assert manager.get_bundle_for_action("list_templates") == Bundle.TEMPLATES
        assert manager.get_bundle_for_action("health_check") == Bundle.ADMIN

        # Test unknown action
        assert manager.get_bundle_for_action("unknown_action") is None

    def test_is_action_allowed(self):
        """Test action bundle validation"""
        manager = BundleManager()

        # Action in correct bundle
        assert manager.is_action_allowed("search_notes", Bundle.CORE) is True

        # Action in wrong bundle
        assert manager.is_action_allowed("search_notes", Bundle.KNOWLEDGE) is False

        # Unknown action
        assert manager.is_action_allowed("unknown", Bundle.CORE) is False

    def test_validate_action_args_valid(self):
        """Test validating valid action arguments"""
        manager = BundleManager()

        # Valid with all required fields
        is_valid, error = manager.validate_action_args(
            "search_notes",
            {"query": "test"}
        )
        assert is_valid is True
        assert error is None

        # Valid with optional fields
        is_valid, error = manager.validate_action_args(
            "search_notes",
            {"query": "test", "limit": 10, "use_regex": True}
        )
        assert is_valid is True
        assert error is None

    def test_validate_action_args_missing_required(self):
        """Test validation fails with missing required fields"""
        manager = BundleManager()

        # Missing required field
        is_valid, error = manager.validate_action_args(
            "search_notes",
            {}
        )
        assert is_valid is False
        assert error is not None
        assert "query" in error

    def test_validate_action_args_unknown_action(self):
        """Test validation fails for unknown action"""
        manager = BundleManager()

        is_valid, error = manager.validate_action_args(
            "unknown_action",
            {}
        )
        assert is_valid is False
        assert "Unknown action" in error

    def test_validate_action_args_unknown_fields(self):
        """Test validation with unknown fields (should warn but not fail)"""
        manager = BundleManager()

        # Unknown fields should be allowed (just warned)
        is_valid, error = manager.validate_action_args(
            "search_notes",
            {"query": "test", "unknown_field": "value"}
        )
        assert is_valid is True  # Should still be valid

    def test_apply_defaults(self):
        """Test applying default values"""
        manager = BundleManager()

        # Apply action defaults
        args = manager.apply_defaults("search_notes", {"query": "test"})

        assert args["query"] == "test"
        assert "limit" in args
        assert args["limit"] == 50  # Default limit
        assert "use_regex" in args
        assert args["use_regex"] is False  # Default

    def test_apply_defaults_override(self):
        """Test defaults don't override provided values"""
        manager = BundleManager()

        args = manager.apply_defaults(
            "search_notes",
            {"query": "test", "limit": 100}
        )

        assert args["limit"] == 100  # Should keep provided value

    def test_enforce_limits_valid(self):
        """Test limit enforcement with valid values"""
        manager = BundleManager()

        # Within limits
        is_valid, error = manager.enforce_limits(
            "search_notes",
            {"query": "test", "limit": 50}
        )
        assert is_valid is True
        assert error is None

    def test_enforce_limits_exceeded(self):
        """Test limit enforcement with exceeded values"""
        manager = BundleManager()

        # Exceed search limit
        is_valid, error = manager.enforce_limits(
            "search_notes",
            {"query": "test", "limit": 1000}
        )
        assert is_valid is False
        assert "exceeds maximum" in error

    def test_enforce_limits_graph_depth(self):
        """Test graph depth limit enforcement"""
        manager = BundleManager()

        # Valid depth
        is_valid, error = manager.enforce_limits(
            "get_graph",
            {"depth": 2}
        )
        assert is_valid is True

        # Exceeded depth
        is_valid, error = manager.enforce_limits(
            "get_graph",
            {"depth": 10}
        )
        assert is_valid is False

    def test_enforce_limits_graph_nodes(self):
        """Test graph max nodes limit enforcement"""
        manager = BundleManager()

        # Valid nodes
        is_valid, error = manager.enforce_limits(
            "get_graph",
            {"max_nodes": 50}
        )
        assert is_valid is True

        # Exceeded nodes
        is_valid, error = manager.enforce_limits(
            "get_graph",
            {"max_nodes": 1000}
        )
        assert is_valid is False

    def test_get_action_info(self):
        """Test getting comprehensive action info"""
        manager = BundleManager()

        info = manager.get_action_info("search_notes")

        assert info is not None
        assert info["name"] == "search_notes"
        assert info["bundle"] == "core"
        assert "required_fields" in info
        assert "optional_fields" in info
        assert "defaults" in info
        assert "bundle_limits" in info
        assert "bundle_defaults" in info

    def test_get_action_info_unknown(self):
        """Test getting info for unknown action"""
        manager = BundleManager()

        info = manager.get_action_info("unknown_action")
        assert info is None

    def test_list_all_actions(self):
        """Test listing all action names"""
        manager = BundleManager()

        actions = manager.list_all_actions()

        assert len(actions) > 0
        assert "search_notes" in actions
        assert "get_backlinks" in actions
        assert "list_templates" in actions
        assert "health_check" in actions

    def test_list_bundle_actions(self):
        """Test listing actions for specific bundle"""
        manager = BundleManager()

        core_actions = manager.list_bundle_actions(Bundle.CORE)

        assert len(core_actions) > 0
        assert "search_notes" in core_actions
        assert "create_note" in core_actions

        # Actions from other bundles should not be included
        assert "get_backlinks" not in core_actions
        assert "list_templates" not in core_actions


class TestBundleLimits:
    """Test bundle limit configurations"""

    def test_core_bundle_limits(self):
        """Test CORE bundle limits"""
        config = BundleDefinitions.get_bundle_config(Bundle.CORE)

        assert "search_limit_max" in config.limits
        assert "list_limit_max" in config.limits
        assert config.limits["search_limit_max"] > 0
        assert config.limits["list_limit_max"] > 0

    def test_knowledge_bundle_limits(self):
        """Test KNOWLEDGE bundle limits"""
        config = BundleDefinitions.get_bundle_config(Bundle.KNOWLEDGE)

        assert "graph_depth_max" in config.limits
        assert "graph_nodes_max" in config.limits
        assert config.limits["graph_depth_max"] == 3
        assert config.limits["graph_nodes_max"] > 0

    def test_templates_bundle_limits(self):
        """Test TEMPLATES bundle limits"""
        config = BundleDefinitions.get_bundle_config(Bundle.TEMPLATES)

        assert "template_depth_max" in config.limits
        assert config.limits["template_depth_max"] == 5


class TestBundleDefaults:
    """Test bundle default configurations"""

    def test_core_bundle_defaults(self):
        """Test CORE bundle defaults"""
        config = BundleDefinitions.get_bundle_config(Bundle.CORE)

        assert "search_limit" in config.defaults
        assert "list_limit" in config.defaults
        assert config.defaults["search_limit"] == 50
        assert config.defaults["list_limit"] == 100

    def test_knowledge_bundle_defaults(self):
        """Test KNOWLEDGE bundle defaults"""
        config = BundleDefinitions.get_bundle_config(Bundle.KNOWLEDGE)

        assert "graph_depth" in config.defaults
        assert "graph_max_nodes" in config.defaults
        assert config.defaults["graph_depth"] == 1
        assert config.defaults["graph_max_nodes"] == 50
