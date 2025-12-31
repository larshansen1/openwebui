"""
Unit tests for intent router
"""

import pytest
from app.mcp.router import IntentRouter, RouteResult, HelpGenerator
from app.mcp.bundles import Bundle


class TestIntentRouter:
    """Test IntentRouter functionality"""

    def test_initialization(self):
        """Test router initialization"""
        router = IntentRouter()
        assert router.bundle_manager is not None

    def test_route_search_intent(self):
        """Test routing search intents"""
        router = IntentRouter()

        test_cases = [
            "search for notes about AI",
            "find notes related to machine learning",
            "look for documents about Python",
            "query notes with tag 'project'",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "search_notes"
            assert result.bundle == "core"
            assert "query" in result.required_fields

    def test_route_list_intent(self):
        """Test routing list intents"""
        router = IntentRouter()

        test_cases = [
            "list all notes",
            "show me all documents",
            "display notes in my vault",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "list_notes"
            assert result.bundle == "core"

    def test_route_read_intent(self):
        """Test routing read intents"""
        router = IntentRouter()

        # Read full content
        result = router.route("read the note called Project Plan")
        assert result.action == "read_note_content"
        assert result.bundle == "core"

        # Get metadata
        result = router.route("get metadata for my note")
        assert result.action == "get_note"
        assert result.bundle == "core"

    def test_route_create_intent(self):
        """Test routing create intents"""
        router = IntentRouter()

        test_cases = [
            "create a new note called Ideas",
            "add a note about today's meeting",
            "make a new document",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "create_note"
            assert result.bundle == "core"

    def test_route_update_intent(self):
        """Test routing update intents"""
        router = IntentRouter()

        test_cases = [
            "update my TODO note",
            "modify the project plan",
            "edit the meeting notes",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "update_note"
            assert result.bundle == "core"

    def test_route_append_intent(self):
        """Test routing append intents"""
        router = IntentRouter()

        test_cases = [
            "append to my journal",
            "add to the daily note",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "append_note"
            assert result.bundle == "core"

    def test_route_delete_intent(self):
        """Test routing delete intents"""
        router = IntentRouter()

        test_cases = [
            "delete the old draft note",
            "remove the temporary file",
            "trash the unused note",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "delete_note"
            assert result.bundle == "core"

    def test_route_move_intent(self):
        """Test routing move intents"""
        router = IntentRouter()

        test_cases = [
            "move the note to archive",
            "rename the file to new name",
            "relocate the document",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "move_note"
            assert result.bundle == "core"

    def test_route_link_resolution_intent(self):
        """Test routing wiki-link resolution intents"""
        router = IntentRouter()

        test_cases = [
            "resolve the wiki-link to Project",
            "resolve link [[Meeting Notes]]",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "resolve_link"
            assert result.bundle == "core"

    def test_route_toc_intent(self):
        """Test routing table of contents intents"""
        router = IntentRouter()

        test_cases = [
            "get table of contents for my note",
            "show me the TOC",
            "get outline of the document",
            "show structure of the note",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_toc"
            assert result.bundle == "core"

    def test_route_section_intent(self):
        """Test routing section operations"""
        router = IntentRouter()

        # Read section
        result = router.route("read the Introduction section")
        assert result.action == "read_section"
        assert result.bundle == "core"

        # Update section
        result = router.route("update the Conclusion section")
        assert result.action == "update_section"
        assert result.bundle == "core"

    def test_route_block_intent(self):
        """Test routing block operations"""
        router = IntentRouter()

        # Read block
        result = router.route("read the block ^important")
        assert result.action == "read_block"
        assert result.bundle == "core"

        # Update block
        result = router.route("update block ^quote-1")
        assert result.action == "update_block"
        assert result.bundle == "core"

    def test_route_backlinks_intent(self):
        """Test routing backlinks intents"""
        router = IntentRouter()

        test_cases = [
            "get backlinks for my note",
            "what links to this page",
            "show me references to Project",
            "find all backlinks",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_backlinks"
            assert result.bundle == "knowledge"

    def test_route_orphans_intent(self):
        """Test routing orphans intents"""
        router = IntentRouter()

        test_cases = [
            "find orphan notes",
            "get orphaned documents",
            "show isolated notes",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_orphans"
            assert result.bundle == "knowledge"

    def test_route_graph_intent(self):
        """Test routing graph intents"""
        router = IntentRouter()

        test_cases = [
            "show me the knowledge graph",
            "get graph of connections",
            "display note network",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_graph"
            assert result.bundle == "knowledge"

    def test_route_tags_intent(self):
        """Test routing tags intents"""
        router = IntentRouter()

        test_cases = [
            "list all tags",
            "show me tags in the vault",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "list_tags"
            assert result.bundle == "knowledge"

    def test_route_templates_list_intent(self):
        """Test routing template list intents"""
        router = IntentRouter()

        test_cases = [
            "list all templates",
            "show me available templates",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "list_templates"
            assert result.bundle == "templates"

    def test_route_templates_create_intent(self):
        """Test routing template create intents"""
        router = IntentRouter()

        test_cases = [
            "create a note from template",
            "use template to create new note",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "create_from_template"
            assert result.bundle == "templates"

    def test_route_templates_save_intent(self):
        """Test routing template save intents"""
        router = IntentRouter()

        result = router.route("save this as a template")
        assert result.action == "save_template"
        assert result.bundle == "templates"

    def test_route_templates_delete_intent(self):
        """Test routing template delete intents"""
        router = IntentRouter()

        result = router.route("delete the old template")
        assert result.action == "delete_template"
        assert result.bundle == "templates"

    def test_route_health_intent(self):
        """Test routing health check intents"""
        router = IntentRouter()

        test_cases = [
            "health check",
            "check status",
            "is the server healthy",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "health_check"
            assert result.bundle == "admin"

    def test_route_stats_intent(self):
        """Test routing stats intents"""
        router = IntentRouter()

        test_cases = [
            "get vault statistics",
            "show me stats",
            "vault summary",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_stats"
            assert result.bundle == "admin"

    def test_route_cache_intent(self):
        """Test routing cache clear intents"""
        router = IntentRouter()

        test_cases = [
            "clear the cache",
            "flush cache",
            "invalidate cache",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "clear_cache"
            assert result.bundle == "admin"

    def test_route_daily_note_intent(self):
        """Test routing daily note intents"""
        router = IntentRouter()

        test_cases = [
            "get today's daily note",
            "show me today's journal",
            "open daily note",
        ]

        for intent in test_cases:
            result = router.route(intent)
            assert result.action == "get_daily_note"
            assert result.bundle == "admin"

    def test_route_with_note_hint(self):
        """Test routing with note hint"""
        router = IntentRouter()

        result = router.route(
            "search for Python",
            note_hint="Project Plan"
        )

        assert result.action == "search_notes"
        assert "Project Plan" in result.reasoning

    def test_route_confidence(self):
        """Test routing confidence scores"""
        router = IntentRouter()

        # High confidence match
        result = router.route("get backlinks for my note")
        assert result.confidence > 0.4

        # Lower confidence (generic)
        result = router.route("get")
        assert result.confidence < 0.5

    def test_route_defaults(self):
        """Test routing includes defaults"""
        router = IntentRouter()

        result = router.route("search for notes")

        assert "limit" in result.defaults
        assert result.defaults["limit"] == 50

    def test_route_limits(self):
        """Test routing includes limits"""
        router = IntentRouter()

        result = router.route("search for notes")

        assert isinstance(result.limits, dict)
        assert "search_limit_max" in result.limits

    def test_route_fallback(self):
        """Test routing falls back to search for unknown intent"""
        router = IntentRouter()

        result = router.route("completely unknown gibberish")

        # Should fallback to search
        assert result.action == "search_notes"
        assert result.confidence < 1.0

    def test_route_with_action(self):
        """Test direct action routing"""
        router = IntentRouter()

        result = router.route_with_action("get_backlinks")

        assert result is not None
        assert result.action == "get_backlinks"
        assert result.bundle == "knowledge"
        assert result.confidence == 1.0

    def test_route_with_invalid_action(self):
        """Test direct routing with invalid action"""
        router = IntentRouter()

        result = router.route_with_action("invalid_action")
        assert result is None

    def test_suggest_bundle(self):
        """Test bundle suggestion from intent"""
        router = IntentRouter()

        # Knowledge bundle keywords
        bundle = router.suggest_bundle("show me backlinks and graph")
        assert bundle == Bundle.KNOWLEDGE

        # Templates bundle keywords
        bundle = router.suggest_bundle("use template to create note")
        assert bundle == Bundle.TEMPLATES

        # Admin bundle keywords
        bundle = router.suggest_bundle("check health and cache stats")
        assert bundle == Bundle.ADMIN

        # No clear match
        bundle = router.suggest_bundle("do something")
        assert bundle is None

    def test_explain_action(self):
        """Test action explanation"""
        router = IntentRouter()

        explanation = router.explain_action("search_notes")

        assert explanation is not None
        assert "search_notes" in explanation
        assert "core" in explanation
        assert "query" in explanation  # Required field

    def test_explain_unknown_action(self):
        """Test explaining unknown action"""
        router = IntentRouter()

        explanation = router.explain_action("unknown_action")
        assert explanation is None

    def test_list_actions_for_bundle(self):
        """Test listing actions for bundle"""
        router = IntentRouter()

        actions = router.list_actions_for_bundle(Bundle.CORE)

        assert len(actions) > 0
        assert "search_notes" in actions
        assert "create_note" in actions

    def test_get_all_actions(self):
        """Test getting all actions"""
        router = IntentRouter()

        actions = router.get_all_actions()

        assert len(actions) > 0
        assert "search_notes" in actions
        assert "get_backlinks" in actions
        assert "list_templates" in actions


class TestHelpGenerator:
    """Test HelpGenerator functionality"""

    def test_get_help_overview_short(self):
        """Test getting overview help (short)"""
        help_text = HelpGenerator.get_help("overview", "short")

        assert help_text is not None
        assert len(help_text) < 500  # Should be short
        assert "obsidian" in help_text.lower()

    def test_get_help_overview_normal(self):
        """Test getting overview help (normal)"""
        help_text = HelpGenerator.get_help("overview", "normal")

        assert help_text is not None
        assert len(help_text) > 100
        assert "obsidian_lookup" in help_text
        assert "obsidian" in help_text
        assert "obsidian_help" in help_text

    def test_get_help_core(self):
        """Test getting core operations help"""
        help_text = HelpGenerator.get_help("core", "normal")

        assert help_text is not None
        assert "search" in help_text.lower()
        assert "create" in help_text.lower()
        assert "section" in help_text.lower()

    def test_get_help_search(self):
        """Test getting search help"""
        help_text = HelpGenerator.get_help("search", "normal")

        assert help_text is not None
        assert "search_notes" in help_text
        assert "list_notes" in help_text

    def test_get_help_read(self):
        """Test getting read operations help"""
        help_text = HelpGenerator.get_help("read", "normal")

        assert help_text is not None
        assert "get_note" in help_text
        assert "read_note_content" in help_text
        assert "read_section" in help_text

    def test_get_help_write(self):
        """Test getting write operations help"""
        help_text = HelpGenerator.get_help("write", "normal")

        assert help_text is not None
        assert "create_note" in help_text
        assert "update_note" in help_text
        assert "delete_note" in help_text

    def test_get_help_templates(self):
        """Test getting templates help"""
        help_text = HelpGenerator.get_help("templates", "normal")

        assert help_text is not None
        assert "template" in help_text.lower()
        assert "{{" in help_text  # Variable syntax

    def test_get_help_graph(self):
        """Test getting knowledge graph help"""
        help_text = HelpGenerator.get_help("graph", "normal")

        assert help_text is not None
        assert "backlinks" in help_text.lower()
        assert "orphan" in help_text.lower()
        assert "graph" in help_text.lower()

    def test_get_help_admin(self):
        """Test getting admin operations help"""
        help_text = HelpGenerator.get_help("admin", "normal")

        assert help_text is not None
        assert "health" in help_text.lower()
        assert "stats" in help_text.lower()
        assert "cache" in help_text.lower()

    def test_get_help_default_topic(self):
        """Test getting help with no topic (default to overview)"""
        help_text = HelpGenerator.get_help(None, "short")

        assert help_text is not None
        assert "obsidian" in help_text.lower()

    def test_get_help_unknown_topic(self):
        """Test getting help for unknown topic"""
        help_text = HelpGenerator.get_help("unknown_topic", "short")

        assert help_text is not None
        assert "Unknown topic" in help_text
        assert "Available topics" in help_text

    def test_list_topics(self):
        """Test listing help topics"""
        topics = HelpGenerator.list_topics()

        assert len(topics) > 0
        assert "overview" in topics
        assert "core" in topics
        assert "search" in topics
        assert "templates" in topics
        assert "graph" in topics
        assert "admin" in topics


class TestRouteResult:
    """Test RouteResult dataclass"""

    def test_route_result_creation(self):
        """Test creating a RouteResult"""
        result = RouteResult(
            bundle="core",
            action="search_notes",
            required_fields=["query"],
            optional_fields=["limit", "tags"],
            defaults={"limit": 50},
            limits={"max_limit": 200},
            confidence=0.8,
            reasoning="Intent matched pattern"
        )

        assert result.bundle == "core"
        assert result.action == "search_notes"
        assert result.required_fields == ["query"]
        assert result.optional_fields == ["limit", "tags"]
        assert result.defaults == {"limit": 50}
        assert result.limits == {"max_limit": 200}
        assert result.confidence == 0.8
        assert result.reasoning == "Intent matched pattern"
