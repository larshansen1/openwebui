"""
MCP Server implementation for Obsidian vault
Exposes vault operations as MCP tools and resources
"""
import logging
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource, EmbeddedResource
from mcp import types
from pathlib import Path

from app.vault.manager import VaultManager

logger = logging.getLogger(__name__)


class ObsidianMCPServer:
    """MCP Server for Obsidian vault operations"""

    def __init__(self, vault_manager: VaultManager):
        """
        Initialize MCP server

        Args:
            vault_manager: VaultManager instance
        """
        self.vault = vault_manager
        self.app = Server("obsidian-mcp")

        # Register tool handlers
        self._register_tools()
        # Register resource handlers
        self._register_resources()

        logger.info("ObsidianMCPServer initialized")

    def _register_tools(self):
        """Register all MCP tools"""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools"""
            return [
                Tool(
                    name="create_note",
                    description="Create a new note in the vault",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title (will be used as filename)"},
                            "content": {"type": "string", "description": "Note content in markdown"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for the note"}
                        },
                        "required": ["title", "content"]
                    }
                ),
                Tool(
                    name="update_note",
                    description="Update an existing note",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to the note"},
                            "content": {"type": "string", "description": "New content (optional if only updating frontmatter)"},
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="move_note",
                    description="Move or rename a note to a new location/path",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "old_path": {"type": "string", "description": "Current relative path to the note"},
                            "new_path": {"type": "string", "description": "New relative path (can include subdirectories like 'folder/subfolder/name')"}
                        },
                        "required": ["old_path", "new_path"]
                    }
                ),
                Tool(
                    name="delete_note",
                    description="Delete a note from the vault",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to the note"}
                        },
                        "required": ["file_path"]
                    }
                ),
                Tool(
                    name="append_to_note",
                    description="Append content to an existing note",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "Relative path to the note"},
                            "content": {"type": "string", "description": "Content to append"}
                        },
                        "required": ["file_path", "content"]
                    }
                ),
                Tool(
                    name="search_notes",
                    description="Search for notes by content and tags with optional regex support",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query (literal string or regex pattern)"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 50},
                            "use_regex": {"type": "boolean", "description": "Treat query as regex pattern", "default": False}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_notes",
                    description="List notes in the vault with optional filtering and sorting",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 100},
                            "sort_by": {"type": "string", "description": "Sort order: 'modified' (default), 'created', 'title', 'size'", "default": "modified", "enum": ["modified", "created", "title", "size"]}
                        }
                    }
                ),
                Tool(
                    name="get_note_by_title",
                    description="Find a note by its title",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to search for"}
                        },
                        "required": ["title"]
                    }
                ),
                Tool(
                    name="resolve_wiki_link",
                    description="Resolve a wiki-link [[Note Name]] to actual file path",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "link_name": {"type": "string", "description": "Wiki-link name (without [[ ]])"}
                        },
                        "required": ["link_name"]
                    }
                ),
                Tool(
                    name="list_tags",
                    description="List all unique tags in the vault",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_note_metadata",
                    description="Get only the metadata/frontmatter of a note without full content (faster than get_note_by_title)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to search for"}
                        },
                        "required": ["title"]
                    }
                ),
                Tool(
                    name="get_daily_note",
                    description="Get or create a daily note for a specific date (follows Obsidian daily notes convention)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format (omit for today)"}
                        }
                    }
                ),
                Tool(
                    name="get_backlinks",
                    description="Get all notes that link to (reference) a specific note - enables bidirectional navigation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Note title to find backlinks for"}
                        },
                        "required": ["title"]
                    }
                ),
                Tool(
                    name="get_orphan_notes",
                    description="Find notes with no backlinks (orphaned/isolated notes that no other notes reference)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Maximum results", "default": 100}
                        }
                    }
                ),
                Tool(
                    name="get_note_graph",
                    description="Get a knowledge graph of notes and their connections (forward links and backlinks)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "center_note": {"type": "string", "description": "Optional note to center the graph around"},
                            "depth": {"type": "integer", "description": "Connection depth to traverse (1-3)", "default": 1, "minimum": 1, "maximum": 3},
                            "max_nodes": {"type": "integer", "description": "Maximum nodes to include", "default": 50}
                        }
                    }
                ),
                # Section/Block Operations
                Tool(
                    name="get_table_of_contents",
                    description="Get hierarchical table of contents from a note with headings and structure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the note"},
                            "max_depth": {"type": "integer", "description": "Maximum heading depth to include (1-6)", "default": 6, "minimum": 1, "maximum": 6}
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="read_section",
                    description="Read a specific section from a note by heading reference",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the note"},
                            "section": {"type": "string", "description": "Section reference (heading text or anchor)"}
                        },
                        "required": ["path", "section"]
                    }
                ),
                Tool(
                    name="read_block",
                    description="Read a specific block from a note by block ID (^block-id)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the note"},
                            "block_id": {"type": "string", "description": "Block ID (without ^ prefix)"}
                        },
                        "required": ["path", "block_id"]
                    }
                ),
                Tool(
                    name="update_section",
                    description="Update a specific section in a note by heading reference",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the note"},
                            "section": {"type": "string", "description": "Section reference (heading text or anchor)"},
                            "content": {"type": "string", "description": "New content for the section (without heading line)"}
                        },
                        "required": ["path", "section", "content"]
                    }
                ),
                Tool(
                    name="update_block",
                    description="Update a specific block in a note by block ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the note"},
                            "block_id": {"type": "string", "description": "Block ID (without ^ prefix)"},
                            "content": {"type": "string", "description": "New content for the block"}
                        },
                        "required": ["path", "block_id", "content"]
                    }
                ),
                Tool(
                    name="list_templates",
                    description="List all available templates in the .templates/ folder",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="create_from_template",
                    description="Create a new note from a template with variable substitution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_name": {"type": "string", "description": "Name of template to use (without .md extension)"},
                            "note_path": {"type": "string", "description": "Path where to create the new note"},
                            "variables": {"type": "object", "description": "Variables for template substitution (e.g., {\"project_name\": \"MyProject\", \"author\": \"John\"})"},
                            "frontmatter": {"type": "object", "description": "Additional frontmatter for the note"}
                        },
                        "required": ["template_name", "note_path"]
                    }
                ),
                Tool(
                    name="save_template",
                    description="Save a template to the .templates/ folder for reuse",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_name": {"type": "string", "description": "Name of template (without .md extension)"},
                            "content": {"type": "string", "description": "Template content with variables like {{variable_name}}"}
                        },
                        "required": ["template_name", "content"]
                    }
                )
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls"""
            try:
                if name == "create_note":
                    return await self._create_note(arguments)
                elif name == "update_note":
                    return await self._update_note(arguments)
                elif name == "move_note":
                    return await self._move_note(arguments)
                elif name == "delete_note":
                    return await self._delete_note(arguments)
                elif name == "append_to_note":
                    return await self._append_to_note(arguments)
                elif name == "search_notes":
                    return await self._search_notes(arguments)
                elif name == "list_notes":
                    return await self._list_notes(arguments)
                elif name == "get_note_by_title":
                    return await self._get_note_by_title(arguments)
                elif name == "resolve_wiki_link":
                    return await self._resolve_wiki_link(arguments)
                elif name == "list_tags":
                    return await self._list_tags(arguments)
                elif name == "get_note_metadata":
                    return await self._get_note_metadata(arguments)
                elif name == "get_daily_note":
                    return await self._get_daily_note(arguments)
                elif name == "get_backlinks":
                    return await self._get_backlinks(arguments)
                elif name == "get_orphan_notes":
                    return await self._get_orphan_notes(arguments)
                elif name == "get_note_graph":
                    return await self._get_note_graph(arguments)
                elif name == "get_table_of_contents":
                    return await self._get_table_of_contents(arguments)
                elif name == "read_section":
                    return await self._read_section(arguments)
                elif name == "read_block":
                    return await self._read_block(arguments)
                elif name == "update_section":
                    return await self._update_section(arguments)
                elif name == "update_block":
                    return await self._update_block(arguments)
                elif name == "list_templates":
                    return await self._list_templates(arguments)
                elif name == "create_from_template":
                    return await self._create_from_template(arguments)
                elif name == "save_template":
                    return await self._save_template(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _register_resources(self):
        """Register MCP resources"""

        @self.app.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="obsidian://vault/stats",
                    name="Vault Statistics",
                    mimeType="application/json",
                    description="Get vault statistics and metadata"
                )
            ]

        @self.app.read_resource()
        async def read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "obsidian://vault/stats":
                import json
                stats = self.vault.get_vault_stats()
                return json.dumps(stats, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")

    # Tool implementation methods

    async def _create_note(self, args: dict) -> list[TextContent]:
        """Create note tool implementation"""
        title = args["title"]
        content = args["content"]
        tags = args.get("tags", [])

        # Build path from title
        path = f"{title}.md" if not title.endswith('.md') else title

        # Build frontmatter
        frontmatter = {}
        if tags:
            frontmatter["tags"] = tags

        result = self.vault.create_note(path, content, frontmatter)

        return [TextContent(
            type="text",
            text=f"Created note: {result['path']}\nTags: {', '.join(result['tags'])}"
        )]

    async def _update_note(self, args: dict) -> list[TextContent]:
        """Update note tool implementation"""
        path = args["file_path"]
        content = args.get("content")

        result = self.vault.update_note(path, content=content)

        return [TextContent(
            type="text",
            text=f"Updated note: {result['path']}\nModified: {result['modified']}"
        )]

    async def _move_note(self, args: dict) -> list[TextContent]:
        """Move note tool implementation"""
        old_path = args["old_path"]
        new_path = args["new_path"]

        result = self.vault.move_note(old_path, new_path)

        return [TextContent(
            type="text",
            text=f"Moved note: {old_path} → {result['path']}\nNew location: {result['path']}"
        )]

    async def _delete_note(self, args: dict) -> list[TextContent]:
        """Delete note tool implementation"""
        path = args["file_path"]

        self.vault.delete_note(path)

        return [TextContent(
            type="text",
            text=f"Deleted note: {path}"
        )]

    async def _append_to_note(self, args: dict) -> list[TextContent]:
        """Append to note tool implementation"""
        path = args["file_path"]
        content = args["content"]

        result = self.vault.update_note(path, content=content, append=True)

        return [TextContent(
            type="text",
            text=f"Appended to note: {result['path']}"
        )]

    async def _search_notes(self, args: dict) -> list[TextContent]:
        """Search notes tool implementation"""
        query = args["query"]
        tags = args.get("tags")
        limit = args.get("limit", 50)
        use_regex = args.get("use_regex", False)

        results = self.vault.search_notes(query, tags, limit, use_regex)

        if not results:
            return [TextContent(type="text", text="No results found")]

        output = f"Found {len(results)} results:\n\n"
        for note in results:
            output += f"**{note['title']}** ({note['path']})\n"
            if note['tags']:
                output += f"Tags: {', '.join(note['tags'])}\n"
            if note['matches']:
                output += "Matches:\n"
                for match in note['matches']:
                    output += f"  - {match}\n"
            output += "\n"

        return [TextContent(type="text", text=output)]

    async def _list_notes(self, args: dict) -> list[TextContent]:
        """List notes tool implementation"""
        tags = args.get("tags")
        limit = args.get("limit", 100)
        sort_by = args.get("sort_by", "modified")

        notes = self.vault.list_notes(include_frontmatter=True, limit=limit, sort_by=sort_by)

        # Filter by tags if provided
        if tags:
            notes = [n for n in notes if any(tag in n.get('tags', []) for tag in tags)]

        output = f"Found {len(notes)} notes:\n\n"
        for note in notes:
            output += f"- **{note['name']}** ({note['path']})\n"
            if 'tags' in note and note['tags']:
                output += f"  Tags: {', '.join(note['tags'])}\n"

        return [TextContent(type="text", text=output)]

    async def _get_note_by_title(self, args: dict) -> list[TextContent]:
        """Get note by title tool implementation"""
        title = args["title"]

        # Try to resolve via wiki-link
        path = self.vault.parser.resolve_wiki_link(title)

        if not path:
            return [TextContent(type="text", text=f"Note not found: {title}")]

        note = self.vault.read_note(path)

        output = f"# {note['name']}\n\n"
        output += f"**Path:** {note['path']}\n"
        output += f"**Tags:** {', '.join(note['tags'])}\n\n"
        output += "## Content\n\n"
        output += note['content']

        return [TextContent(type="text", text=output)]

    async def _resolve_wiki_link(self, args: dict) -> list[TextContent]:
        """Resolve wiki-link tool implementation"""
        link_name = args["link_name"]

        path = self.vault.parser.resolve_wiki_link(link_name)

        if path:
            return [TextContent(type="text", text=f"Resolved: [[{link_name}]] → {path}")]
        else:
            return [TextContent(type="text", text=f"Could not resolve: [[{link_name}]]")]

    async def _list_tags(self, args: dict) -> list[TextContent]:
        """List tags tool implementation"""
        # Collect all tags from vault
        tags_count = {}

        notes = self.vault.list_notes(include_frontmatter=True, limit=10000)
        for note in notes:
            for tag in note.get('tags', []):
                tags_count[tag] = tags_count.get(tag, 0) + 1

        # Sort by count
        sorted_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)

        output = f"Found {len(sorted_tags)} unique tags:\n\n"
        for tag, count in sorted_tags:
            output += f"- {tag} ({count} notes)\n"

        return [TextContent(type="text", text=output)]

    async def _get_note_metadata(self, args: dict) -> list[TextContent]:
        """Get note metadata tool implementation"""
        title = args["title"]

        try:
            metadata = self.vault.get_note_metadata(title)

            output = f"# Metadata for: {metadata['name']}\n\n"
            output += f"**Path:** {metadata['path']}\n"
            output += f"**Match Score:** {metadata['match_score']:.2f} ({metadata['match_type']})\n"
            output += f"**Tags:** {', '.join(metadata['tags']) if metadata['tags'] else 'None'}\n"
            output += f"**Size:** {metadata['size']} bytes\n"
            output += f"**Created:** {metadata['created']}\n"
            output += f"**Modified:** {metadata['modified']}\n\n"

            if metadata['frontmatter']:
                output += "## Frontmatter\n\n"
                for key, value in metadata['frontmatter'].items():
                    output += f"- **{key}:** {value}\n"

            return [TextContent(type="text", text=output)]
        except FileNotFoundError:
            return [TextContent(type="text", text=f"Note not found: {title}")]

    async def _get_daily_note(self, args: dict) -> list[TextContent]:
        """Get daily note tool implementation"""
        date = args.get("date")

        try:
            note = self.vault.get_daily_note(date)

            output = f"# Daily Note: {note['name']}\n\n"
            output += f"**Path:** {note['path']}\n"
            output += f"**Tags:** {', '.join(note['tags'])}\n"
            output += f"**Modified:** {note['modified']}\n\n"
            output += "## Content\n\n"
            output += note['content']

            return [TextContent(type="text", text=output)]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_backlinks(self, args: dict) -> list[TextContent]:
        """Get backlinks tool implementation"""
        title = args["title"]

        try:
            result = self.vault.get_backlinks(title)

            if result["backlink_count"] == 0:
                output = f"# Backlinks for: {result['note_name']}\n\n"
                output += "No backlinks found. This note is not referenced by any other notes."
            else:
                output = f"# Backlinks for: {result['note_name']}\n\n"
                output += f"**Path:** {result['note_path']}\n"
                output += f"**Referenced by {result['backlink_count']} note(s):**\n\n"

                for backlink in result["backlinks"]:
                    output += f"### {backlink['source_name']}\n"
                    output += f"- **Path:** {backlink['source_path']}\n"
                    output += f"- **Context:** {backlink['context']}\n\n"

            return [TextContent(type="text", text=output)]
        except FileNotFoundError:
            return [TextContent(type="text", text=f"Note not found: {title}")]

    async def _get_orphan_notes(self, args: dict) -> list[TextContent]:
        """Get orphan notes tool implementation"""
        limit = args.get("limit", 100)

        orphans = self.vault.get_orphan_notes(limit)

        if not orphans:
            return [TextContent(type="text", text="No orphan notes found. All notes are referenced!")]

        output = f"# Orphan Notes ({len(orphans)} found)\n\n"
        output += "Notes with no backlinks (not referenced by any other notes):\n\n"

        for orphan in orphans:
            output += f"- **{orphan['name']}** ({orphan['path']})\n"
            output += f"  - Size: {orphan['size']} bytes\n"
            output += f"  - Modified: {orphan['modified']}\n\n"

        return [TextContent(type="text", text=output)]

    async def _get_note_graph(self, args: dict) -> list[TextContent]:
        """Get note graph tool implementation"""
        center_note = args.get("center_note")
        depth = args.get("depth", 1)
        max_nodes = args.get("max_nodes", 50)

        try:
            graph = self.vault.get_note_graph(center_note, depth, max_nodes)

            output = f"# Knowledge Graph\n\n"

            if graph["center_note"]:
                output += f"**Centered on:** {graph['center_note']}\n"

            output += f"**Depth:** {depth} level(s)\n"
            output += f"**Nodes:** {graph['node_count']}\n"
            output += f"**Edges:** {graph['edge_count']}\n\n"

            # Show top connected nodes
            sorted_nodes = sorted(
                graph["nodes"],
                key=lambda n: n["backlink_count"] + n["forward_link_count"],
                reverse=True
            )[:10]

            output += "## Most Connected Notes\n\n"
            for node in sorted_nodes:
                output += f"### {node['name']}\n"
                output += f"- **Path:** {node['id']}\n"
                output += f"- **Forward links:** {node['forward_link_count']}\n"
                output += f"- **Backlinks:** {node['backlink_count']}\n"
                output += f"- **Tags:** {', '.join(node['tags']) if node['tags'] else 'None'}\n\n"

            # Show connections
            if graph["edges"]:
                output += f"## Connections ({len(graph['edges'])} edges)\n\n"
                for edge in graph["edges"][:20]:  # Limit to first 20
                    from_name = next((n["name"] for n in graph["nodes"] if n["id"] == edge["from"]), edge["from"])
                    to_name = next((n["name"] for n in graph["nodes"] if n["id"] == edge["to"]), edge["to"])
                    output += f"- {from_name} → {to_name} ({edge['type']})\n"

                if len(graph["edges"]) > 20:
                    output += f"\n... and {len(graph['edges']) - 20} more connections\n"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error generating graph: {str(e)}")]

    # Section/Block operation handlers

    async def _get_table_of_contents(self, args: dict) -> list[TextContent]:
        """Get table of contents tool implementation"""
        path = args["path"]
        max_depth = args.get("max_depth", 6)

        try:
            result = self.vault.get_table_of_contents(path, max_depth)

            output = f"# Table of Contents: {path}\n\n"
            output += f"**Headings:** {result['heading_count']}\n"
            output += f"**Word Count:** {result['word_count']}\n"
            output += f"**Reading Time:** {result['reading_time_minutes']} minutes\n\n"

            if not result['toc']:
                output += "No headings found in this note.\n"
            else:
                output += "## Structure\n\n"
                for entry in result['toc']:
                    indent = "  " * (entry['level'] - 1)
                    output += f"{indent}- {entry['text']} (#{entry['anchor']}, line {entry['line']})\n"

            return [TextContent(type="text", text=output)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting TOC: {str(e)}")]

    async def _read_section(self, args: dict) -> list[TextContent]:
        """Read section tool implementation"""
        path = args["path"]
        section = args["section"]

        try:
            result = self.vault.read_section(path, section)

            output = f"# Section: {result['heading_text']}\n\n"
            output += f"**Path:** {path}\n"
            output += f"**Level:** H{result['heading_level']}\n"
            output += f"**Reference:** {section}\n\n"
            output += "## Content\n\n"
            output += result['content']

            return [TextContent(type="text", text=output)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading section: {str(e)}")]

    async def _read_block(self, args: dict) -> list[TextContent]:
        """Read block tool implementation"""
        path = args["path"]
        block_id = args["block_id"]

        try:
            result = self.vault.read_block(path, block_id)

            output = f"# Block: ^{block_id}\n\n"
            output += f"**Path:** {path}\n"
            output += f"**Block ID:** {block_id}\n\n"
            output += "## Content\n\n"
            output += result['content']

            return [TextContent(type="text", text=output)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error reading block: {str(e)}")]

    async def _update_section(self, args: dict) -> list[TextContent]:
        """Update section tool implementation"""
        path = args["path"]
        section = args["section"]
        content = args["content"]

        try:
            result = self.vault.update_section(path, section, content)

            output = f"# Section Updated\n\n"
            output += f"**Path:** {path}\n"
            output += f"**Section:** {section}\n"
            output += f"**Status:** Successfully updated\n\n"
            output += f"Note now has {result['size']} bytes and {len(result['content'].split())} words.\n"

            return [TextContent(type="text", text=output)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error updating section: {str(e)}")]

    async def _update_block(self, args: dict) -> list[TextContent]:
        """Update block tool implementation"""
        path = args["path"]
        block_id = args["block_id"]
        content = args["content"]

        try:
            result = self.vault.update_block(path, block_id, content)

            output = f"# Block Updated\n\n"
            output += f"**Path:** {path}\n"
            output += f"**Block ID:** ^{block_id}\n"
            output += f"**Status:** Successfully updated\n\n"
            output += f"Note now has {result['size']} bytes and {len(result['content'].split())} words.\n"

            return [TextContent(type="text", text=output)]
        except FileNotFoundError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error updating block: {str(e)}")]

    async def _list_templates(self, args: dict) -> list[TextContent]:
        """List templates tool implementation"""
        try:
            result = self.vault.list_templates()

            output = f"# Available Templates\n\n"
            output += f"**Count:** {result['count']}\n"
            output += f"**Directory:** {result['templates_directory']}\n\n"

            if result['templates']:
                for template in result['templates']:
                    output += f"## {template['name']}\n"
                    if template['variables']:
                        output += f"**Variables:** {', '.join(template['variables'])}\n"
                    if template['extends']:
                        output += f"**Extends:** {template['extends']}\n"
                    if template['includes']:
                        output += f"**Includes:** {', '.join(template['includes'])}\n"
                    output += "\n"
            else:
                output += "No templates found.\n"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing templates: {str(e)}")]

    async def _create_from_template(self, args: dict) -> list[TextContent]:
        """Create from template tool implementation"""
        template_name = args["template_name"]
        note_path = args["note_path"]
        variables = args.get("variables", {})
        frontmatter = args.get("frontmatter", {})

        try:
            result = self.vault.create_from_template(
                template_name,
                note_path,
                variables,
                frontmatter
            )

            output = f"# Note Created from Template\n\n"
            output += f"**Template:** {template_name}\n"
            output += f"**Path:** {note_path}\n"
            output += f"**Size:** {result['size']} bytes\n"
            output += f"**Status:** Successfully created\n\n"

            if variables:
                output += f"**Variables used:** {', '.join(variables.keys())}\n"

            return [TextContent(type="text", text=output)]
        except FileExistsError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating note from template: {str(e)}")]

    async def _save_template(self, args: dict) -> list[TextContent]:
        """Save template tool implementation"""
        template_name = args["template_name"]
        content = args["content"]

        try:
            result = self.vault.save_template(template_name, content)

            output = f"# Template Saved\n\n"
            output += f"**Name:** {result['name']}\n"
            output += f"**Path:** {result['template_path']}\n"

            if result['variables']:
                output += f"**Variables:** {', '.join(result['variables'])}\n"
            if result['extends']:
                output += f"**Extends:** {result['extends']}\n"
            if result['includes']:
                output += f"**Includes:** {', '.join(result['includes'])}\n"

            output += f"\n**Status:** Successfully saved\n"

            return [TextContent(type="text", text=output)]
        except ValueError as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error saving template: {str(e)}")]

    def get_app(self) -> Server:
        """Get MCP server application"""
        return self.app
