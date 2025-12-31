"""
Intent router for dynamic tool loading.

Routes user intent to appropriate bundle and action using keyword matching
and pattern detection.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re
import logging

from app.mcp.bundles import Bundle, BundleManager, BundleDefinitions

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result of intent routing"""
    bundle: str  # Bundle name
    action: str  # Action name
    required_fields: List[str]
    optional_fields: List[str]
    defaults: Dict[str, Any]
    limits: Dict[str, Any]
    confidence: float  # 0.0-1.0 confidence in routing decision
    reasoning: str  # Explanation of routing decision


class IntentRouter:
    """Routes user intent to appropriate bundle and action"""

    # Intent patterns for action detection
    # Format: (pattern, action_name, confidence_boost)
    INTENT_PATTERNS = [
        # Search operations
        (r'\b(search|find|look\s+for|query)\b.*\b(notes?|documents?)\b', 'search_notes', 0.3),
        (r'\bsearch\b', 'search_notes', 0.2),
        (r'\bfind\b.*\babout\b', 'search_notes', 0.2),

        # List operations
        (r'\b(list|show|display)\b.*\b(all\s+)?notes?\b', 'list_notes', 0.3),
        (r'\blist\b', 'list_notes', 0.1),

        # Get/Read operations
        (r'\b(get|read|show|open)\b.*\b(note|content|full)\b', 'read_note_content', 0.3),
        (r'\b(get|fetch)\b.*\b(metadata|info|information)\b', 'get_note', 0.3),
        (r'\bget\b', 'get_note', 0.1),
        (r'\bread\b', 'read_note_content', 0.2),

        # Create operations
        (r'\b(create|new|add|make)\b.*\bnote\b', 'create_note', 0.3),
        (r'\bcreate\b', 'create_note', 0.1),

        # Update operations
        (r'\b(update|modify|change|edit)\b.*\bnote\b', 'update_note', 0.3),
        (r'\bupdate\b', 'update_note', 0.2),
        (r'\bedit\b', 'update_note', 0.2),

        # Append operations
        (r'\b(append|add\s+to)\b', 'append_note', 0.3),

        # Delete operations
        (r'\b(delete|remove|trash)\b.*\bnote\b', 'delete_note', 0.3),
        (r'\bdelete\b', 'delete_note', 0.2),

        # Move operations
        (r'\b(move|rename|relocate)\b.*\bnote\b', 'move_note', 0.3),
        (r'\bmove\b', 'move_note', 0.2),
        (r'\brename\b', 'move_note', 0.2),

        # Link resolution
        (r'\bresolve\b.*\b(link|wiki)', 'resolve_link', 0.4),
        (r'\bwiki.?link\b', 'resolve_link', 0.3),

        # TOC operations
        (r'\b(toc|table\s+of\s+contents|outline|structure)\b', 'get_toc', 0.4),
        (r'\bheadings?\b', 'get_toc', 0.2),

        # Section operations
        (r'\bread\b.*\bsection\b', 'read_section', 0.4),
        (r'\bupdate\b.*\bsection\b', 'update_section', 0.4),
        (r'\bsection\b', 'read_section', 0.2),

        # Block operations
        (r'\bread\b.*\bblock\b', 'read_block', 0.4),
        (r'\bupdate\b.*\bblock\b', 'update_block', 0.4),
        (r'\bblock\b.*\^', 'read_block', 0.3),

        # Backlinks (Knowledge bundle)
        (r'\b(backlinks?|references?|links?\s+to|what\s+links)\b', 'get_backlinks', 0.4),
        (r'\bbacklinks?\b', 'get_backlinks', 0.5),

        # Orphans (Knowledge bundle)
        (r'\b(orphans?|orphaned|isolated|unlinked)\b.*\bnotes?\b', 'get_orphans', 0.5),
        (r'\borphans?\b', 'get_orphans', 0.4),

        # Graph (Knowledge bundle)
        (r'\b(graph|network|connections?|map)\b.*\b(notes?|knowledge)\b', 'get_graph', 0.4),
        (r'\bgraph\b', 'get_graph', 0.3),
        (r'\bknowledge\s+graph\b', 'get_graph', 0.5),

        # Tags (Knowledge bundle)
        (r'\b(list|show|all)\b.*\btags?\b', 'list_tags', 0.4),
        (r'\btags?\b.*\b(list|all)\b', 'list_tags', 0.4),

        # Templates
        (r'\b(list|show)\b.*\btemplates?\b', 'list_templates', 0.4),
        (r'\b(create|new)\b.*\b(from\s+)?template\b', 'create_from_template', 0.5),
        (r'\bsave\b.*\btemplate\b', 'save_template', 0.4),
        (r'\bdelete\b.*\btemplate\b', 'delete_template', 0.4),
        (r'\btemplate\b', 'list_templates', 0.1),

        # Admin
        (r'\b(health|status|check)\b', 'health_check', 0.4),
        (r'\b(stats|statistics|summary)\b', 'get_stats', 0.3),
        (r'\b(clear|flush|invalidate)\b.*\bcache\b', 'clear_cache', 0.5),
        (r'\b(daily\s+note|today|journal)\b', 'get_daily_note', 0.4),
    ]

    # Bundle keywords for bundle-specific routing
    BUNDLE_KEYWORDS = {
        Bundle.KNOWLEDGE: ['backlink', 'orphan', 'graph', 'network', 'connection', 'reference'],
        Bundle.TEMPLATES: ['template', 'boilerplate', 'scaffold'],
        Bundle.ADMIN: ['health', 'stats', 'cache', 'daily', 'journal'],
    }

    def __init__(self):
        """Initialize intent router"""
        self.bundle_manager = BundleManager()

    def route(
        self,
        intent: str,
        note_hint: Optional[str] = None
    ) -> RouteResult:
        """
        Route user intent to bundle and action

        Args:
            intent: User's intent description
            note_hint: Optional note title/path hint

        Returns:
            RouteResult with routing decision
        """
        intent_lower = intent.lower()

        # Score all actions
        action_scores: Dict[str, float] = {}

        for pattern, action_name, confidence_boost in self.INTENT_PATTERNS:
            if re.search(pattern, intent_lower, re.IGNORECASE):
                action_scores[action_name] = action_scores.get(action_name, 0.0) + confidence_boost

        # If no patterns matched, use default
        if not action_scores:
            logger.warning(f"No pattern matched for intent: {intent}")
            action_scores['search_notes'] = 0.5  # Default to search

        # Select action with highest score
        action_name = max(action_scores, key=action_scores.get)
        confidence = min(action_scores[action_name], 1.0)

        # Get action definition
        action_def = BundleDefinitions.get_action(action_name)
        if not action_def:
            # Fallback to search
            action_def = BundleDefinitions.get_action('search_notes')
            confidence = 0.3
            action_name = 'search_notes'

        # Get bundle config
        bundle_config = BundleDefinitions.get_bundle_config(action_def.bundle)

        # Build reasoning
        reasoning = f"Intent '{intent[:50]}...' matched action '{action_name}' in bundle '{action_def.bundle.value}'"
        if note_hint:
            reasoning += f" (note hint: '{note_hint}')"

        return RouteResult(
            bundle=action_def.bundle.value,
            action=action_name,
            required_fields=action_def.required_fields,
            optional_fields=action_def.optional_fields,
            defaults=action_def.defaults,
            limits=bundle_config.limits if bundle_config else {},
            confidence=confidence,
            reasoning=reasoning
        )

    def route_with_action(self, action_name: str) -> Optional[RouteResult]:
        """
        Route directly to a specific action (bypass intent detection)

        Args:
            action_name: Specific action to route to

        Returns:
            RouteResult if action exists, None otherwise
        """
        action_def = BundleDefinitions.get_action(action_name)
        if not action_def:
            return None

        bundle_config = BundleDefinitions.get_bundle_config(action_def.bundle)

        return RouteResult(
            bundle=action_def.bundle.value,
            action=action_name,
            required_fields=action_def.required_fields,
            optional_fields=action_def.optional_fields,
            defaults=action_def.defaults,
            limits=bundle_config.limits if bundle_config else {},
            confidence=1.0,
            reasoning=f"Direct action routing to '{action_name}'"
        )

    def suggest_bundle(self, intent: str) -> Optional[Bundle]:
        """
        Suggest a bundle based on intent keywords

        Args:
            intent: User's intent description

        Returns:
            Suggested Bundle or None
        """
        intent_lower = intent.lower()

        bundle_scores: Dict[Bundle, int] = {}

        for bundle, keywords in self.BUNDLE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in intent_lower)
            if score > 0:
                bundle_scores[bundle] = score

        if not bundle_scores:
            return None

        return max(bundle_scores, key=bundle_scores.get)

    def explain_action(self, action_name: str) -> Optional[str]:
        """
        Get human-readable explanation of an action

        Args:
            action_name: Action to explain

        Returns:
            Explanation string or None if action not found
        """
        action_def = BundleDefinitions.get_action(action_name)
        if not action_def:
            return None

        explanation = f"**{action_name}** ({action_def.bundle.value} bundle)\n"
        explanation += f"{action_def.description}\n\n"

        if action_def.required_fields:
            explanation += f"Required: {', '.join(action_def.required_fields)}\n"

        if action_def.optional_fields:
            explanation += f"Optional: {', '.join(action_def.optional_fields)}\n"

        if action_def.defaults:
            defaults_str = ', '.join(f"{k}={v}" for k, v in action_def.defaults.items())
            explanation += f"Defaults: {defaults_str}\n"

        return explanation

    def list_actions_for_bundle(self, bundle: Bundle) -> List[str]:
        """List all action names in a bundle"""
        return self.bundle_manager.list_bundle_actions(bundle)

    def get_all_actions(self) -> List[str]:
        """Get all available action names"""
        return self.bundle_manager.list_all_actions()


class HelpGenerator:
    """Generate help content for obsidian_help tool"""

    HELP_TOPICS = {
        "overview": {
            "short": "Obsidian vault operations: search, read, write, organize notes. Use obsidian_lookup to plan actions, obsidian to execute.",
            "normal": """Obsidian MCP provides vault operations through 3 tools:
- obsidian_lookup: Plan an action (discover what's available)
- obsidian: Execute an action (perform vault operations)
- obsidian_help: Get help (this command)

Capabilities:
- Search and list notes
- Read/write note content
- Navigate with wiki-links
- Work with sections and blocks
- Manage backlinks and knowledge graph
- Use templates
- Get vault statistics

Example: "find notes about AI" → obsidian_lookup → obsidian(search_notes)"""
        },
        "core": {
            "short": "Search, list, read, create, update, delete, move notes. Work with sections (headings) and blocks.",
            "normal": """Core operations (core bundle):

Search & Discovery:
- search_notes: Find notes by content/tags (supports regex)
- list_notes: List all notes with filtering/sorting
- get_note: Get metadata without full content
- read_note_content: Read full note content

CRUD Operations:
- create_note: Create new note
- update_note: Update existing note
- append_note: Append to note
- delete_note: Delete note
- move_note: Move/rename note

Structure Operations:
- get_toc: Get table of contents
- read_section: Read specific section by heading
- update_section: Update section content
- read_block: Read block by ^block-id
- update_block: Update block content

Example: "update the Introduction section in my README note\""""
        },
        "search": {
            "short": "search_notes (content/tags/regex) and list_notes (filter/sort).",
            "normal": """Search Operations:

search_notes:
- Search by content and tags
- Optional regex support
- Limit results (default: 50)
- Example: "search for notes about machine learning with tag 'AI'"

list_notes:
- List all notes in vault
- Filter by tags
- Sort by: modified, created, title, size
- Limit results (default: 100)
- Example: "list recent notes sorted by modified date\""""
        },
        "read": {
            "short": "get_note (metadata only), read_note_content (full), read_section (by heading), read_block (by ^id).",
            "normal": """Read Operations:

get_note:
- Get metadata without full content (faster)
- Returns: title, path, tags, size, dates
- Example: "get metadata for 'Project Plan' note"

read_note_content:
- Read full note content
- Use when you actually need the content
- Example: "read the full content of my meeting notes"

read_section:
- Read specific section by heading
- Supports fuzzy heading matching
- Example: "read the 'Next Steps' section from my TODO note"

read_block:
- Read block by ^block-id
- Precise block-level reading
- Example: "read block ^important-quote from my notes\""""
        },
        "write": {
            "short": "create_note, update_note, append_note, delete_note, move_note, update_section, update_block.",
            "normal": """Write Operations:

create_note:
- Create new note with content
- Optional tags and frontmatter
- Example: "create a new note called 'Ideas' with some thoughts"

update_note:
- Update existing note content
- Can update frontmatter only
- Example: "update my TODO note with new tasks"

append_note:
- Append content to end of note
- Preserves existing content
- Example: "append today's meeting notes to the team journal"

delete_note:
- Delete a note
- Cannot be undone
- Example: "delete the draft note"

move_note:
- Move or rename note
- Can include subdirectories
- Example: "move 'Draft.md' to 'Archive/2024/Draft.md'\"

Section/Block Updates:
- update_section: Update content under a heading
- update_block: Update specific block by ^id"""
        },
        "templates": {
            "short": "list_templates, create_from_template, save_template. Variables: {{name}}, macros: {{date}}, {{time}}.",
            "normal": """Template Operations:

list_templates:
- List all available templates
- Shows variables and inheritance
- Example: "show me available templates"

create_from_template:
- Create note from template
- Variable substitution ({{variable}})
- Built-in macros: {{date}}, {{time}}, {{datetime}}
- Example: "create a meeting note from the 'meeting' template"

save_template:
- Save new template
- Templates stored in .templates/ folder
- Use {{variable_name}} for substitution
- Example: "save this as a template called 'project-plan'\"

Templates support:
- Variables: {{project_name}}, {{author}}
- Date macros: {{date:%Y-%m-%d}}, {{time}}
- Inheritance: {% extends "base" %}
- Includes: {% include "header" %}"""
        },
        "graph": {
            "short": "get_backlinks (what links here), get_orphans (isolated notes), get_graph (connections), list_tags.",
            "normal": """Knowledge Graph Operations:

get_backlinks:
- Find all notes that link to a target note
- Shows bidirectional connections
- Example: "what notes link to my 'Machine Learning' note?"

get_orphans:
- Find notes with no backlinks
- Discover isolated/unused notes
- Limit results (default: 100)
- Example: "find orphaned notes in my vault"

get_graph:
- Get knowledge graph of connections
- Center on specific note (optional)
- Control depth (1-3) and max nodes
- Shows forward links and backlinks
- Example: "show me the knowledge graph centered on 'Projects'"

list_tags:
- List all unique tags in vault
- Shows tag usage counts
- Example: "what tags are in my vault?\""""
        },
        "admin": {
            "short": "health_check, get_stats, clear_cache, get_daily_note.",
            "normal": """Administrative Operations:

health_check:
- Check server health status
- Vault accessibility
- Example: "is the server healthy?"

get_stats:
- Get vault statistics
- Total notes, size, tags, etc.
- Example: "show me vault statistics"

clear_cache:
- Clear cache entries
- Optional pattern matching
- Example: "clear all caches"

get_daily_note:
- Get or create daily note
- Follows Obsidian daily notes convention
- Optional date (default: today)
- Example: "get today's daily note\""""
        }
    }

    @classmethod
    def get_help(
        cls,
        topic: Optional[str] = None,
        verbosity: str = "short"
    ) -> str:
        """
        Generate help content

        Args:
            topic: Help topic (overview, core, search, etc.)
            verbosity: short or normal

        Returns:
            Help text
        """
        if topic is None:
            topic = "overview"

        if topic not in cls.HELP_TOPICS:
            available = ", ".join(cls.HELP_TOPICS.keys())
            return f"Unknown topic: {topic}\nAvailable topics: {available}"

        topic_content = cls.HELP_TOPICS[topic]

        if verbosity == "short":
            return topic_content["short"]
        else:
            return topic_content["normal"]

    @classmethod
    def list_topics(cls) -> List[str]:
        """Get all available help topics"""
        return list(cls.HELP_TOPICS.keys())
