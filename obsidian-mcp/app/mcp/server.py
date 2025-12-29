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
                    description="Search for notes by content and tags",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_notes",
                    description="List notes in the vault with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                            "limit": {"type": "integer", "description": "Maximum results", "default": 100}
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

        results = self.vault.search_notes(query, tags, limit)

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

        notes = self.vault.list_notes(include_frontmatter=True, limit=limit)

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

    def get_app(self) -> Server:
        """Get MCP server application"""
        return self.app
