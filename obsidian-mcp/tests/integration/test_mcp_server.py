"""
Integration tests for MCP Server (app/mcp/server.py)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.mcp.server import ObsidianMCPServer
from mcp.types import TextContent


@pytest.fixture
def mcp_server(vault_manager):
    """Create MCP server instance"""
    return ObsidianMCPServer(vault_manager)


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPServerInitialization:
    """Test MCP server initialization"""

    async def test_server_initialization(self, mcp_server):
        """Test server initializes correctly"""
        assert mcp_server.vault is not None

    async def test_list_tools(self, mcp_server):
        """Test listing available tools"""
        result = await mcp_server.list_tools()

        # Should have 16 tools (11 original + 5 new features)
        assert len(result.tools) == 16

        # Check some tool names
        tool_names = [tool.name for tool in result.tools]
        assert "create_note" in tool_names
        assert "search_notes" in tool_names
        assert "get_backlinks" in tool_names
        assert "get_note_graph" in tool_names


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPCreateNote:
    """Test MCP create_note tool"""

    async def test_create_note_success(self, mcp_server):
        """Test creating note via MCP"""
        args = {
            "title": "MCP Test Note",
            "content": "Created via MCP",
            "tags": ["mcp", "test"]
        }

        result = await mcp_server.call_tool("create_note", args)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "MCP Test Note" in result[0].text

    async def test_create_note_duplicate(self, mcp_server):
        """Test creating duplicate note via MCP"""
        args = {
            "title": "Welcome",
            "content": "Duplicate",
            "tags": []
        }

        result = await mcp_server.call_tool("create_note", args)

        assert "already exists" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPReadNote:
    """Test MCP read_note tool"""

    async def test_read_note_success(self, mcp_server):
        """Test reading note via MCP"""
        args = {
            "title": "Welcome"
        }

        result = await mcp_server.call_tool("read_note", args)

        assert len(result) == 1
        assert "Welcome to the Test Vault" in result[0].text

    async def test_read_note_not_found(self, mcp_server):
        """Test reading non-existent note"""
        args = {
            "title": "Nonexistent"
        }

        result = await mcp_server.call_tool("read_note", args)

        assert "not found" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPUpdateNote:
    """Test MCP update_note tool"""

    async def test_update_note_success(self, mcp_server):
        """Test updating note via MCP"""
        args = {
            "file_path": "Welcome.md",
            "content": "Updated via MCP"
        }

        result = await mcp_server.call_tool("update_note", args)

        assert "Updated successfully" in result[0].text

    async def test_update_note_not_found(self, mcp_server):
        """Test updating non-existent note"""
        args = {
            "file_path": "nonexistent.md",
            "content": "New content"
        }

        result = await mcp_server.call_tool("update_note", args)

        assert "not found" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPAppendToNote:
    """Test MCP append_to_note tool"""

    async def test_append_to_note_success(self, mcp_server):
        """Test appending to note via MCP"""
        args = {
            "file_path": "Welcome.md",
            "content": "Appended via MCP"
        }

        result = await mcp_server.call_tool("append_to_note", args)

        assert "added successfully" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPSearchNotes:
    """Test MCP search_notes tool"""

    async def test_search_basic(self, mcp_server):
        """Test basic search via MCP"""
        args = {
            "query": "vault",
            "limit": 50,
            "use_regex": False
        }

        result = await mcp_server.call_tool("search_notes", args)

        assert len(result) == 1
        assert "results found" in result[0].text.lower()

    async def test_search_with_regex(self, mcp_server):
        """Test regex search via MCP"""
        args = {
            "query": r"\[\[.*?\]\]",
            "limit": 50,
            "use_regex": True
        }

        result = await mcp_server.call_tool("search_notes", args)

        assert len(result) == 1

    async def test_search_with_tags(self, mcp_server):
        """Test search with tags via MCP"""
        args = {
            "query": "",
            "tags": ["meta"],
            "limit": 50,
            "use_regex": False
        }

        result = await mcp_server.call_tool("search_notes", args)

        assert len(result) == 1


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPListNotes:
    """Test MCP list_notes tool"""

    async def test_list_all_notes(self, mcp_server):
        """Test listing all notes via MCP"""
        args = {
            "directory": "",
            "recursive": True,
            "include_frontmatter": False,
            "limit": 100,
            "offset": 0,
            "sort_by": "modified"
        }

        result = await mcp_server.call_tool("list_notes", args)

        assert len(result) == 1
        assert "notes found" in result[0].text.lower()

    async def test_list_with_sort_by_title(self, mcp_server):
        """Test listing with title sort via MCP"""
        args = {
            "sort_by": "title",
            "limit": 100,
            "recursive": True
        }

        result = await mcp_server.call_tool("list_notes", args)

        assert len(result) == 1


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetNoteMetadata:
    """Test MCP get_note_metadata tool"""

    async def test_get_metadata_success(self, mcp_server):
        """Test getting metadata via MCP"""
        args = {
            "title": "Welcome"
        }

        result = await mcp_server.call_tool("get_note_metadata", args)

        assert len(result) == 1
        assert "Welcome" in result[0].text
        # Should not include full content in output


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetDailyNote:
    """Test MCP get_daily_note tool"""

    async def test_get_daily_note_today(self, mcp_server):
        """Test getting today's daily note via MCP"""
        args = {}

        result = await mcp_server.call_tool("get_daily_note", args)

        assert len(result) == 1
        assert "Daily Note" in result[0].text

    async def test_get_daily_note_specific_date(self, mcp_server):
        """Test getting daily note for specific date via MCP"""
        args = {
            "date": "2025-01-01"
        }

        result = await mcp_server.call_tool("get_daily_note", args)

        assert "2025-01-01" in result[0].text

    async def test_get_daily_note_invalid_date(self, mcp_server):
        """Test getting daily note with invalid date via MCP"""
        args = {
            "date": "invalid"
        }

        result = await mcp_server.call_tool("get_daily_note", args)

        assert "invalid" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetBacklinks:
    """Test MCP get_backlinks tool"""

    async def test_get_backlinks_success(self, mcp_server):
        """Test getting backlinks via MCP"""
        args = {
            "title": "Projects"
        }

        result = await mcp_server.call_tool("get_backlinks", args)

        assert len(result) == 1
        assert "Backlinks for" in result[0].text

    async def test_get_backlinks_no_backlinks(self, mcp_server):
        """Test getting backlinks for orphan note via MCP"""
        args = {
            "title": "Orphan Note"
        }

        result = await mcp_server.call_tool("get_backlinks", args)

        assert "No backlinks found" in result[0].text


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetOrphanNotes:
    """Test MCP get_orphan_notes tool"""

    async def test_get_orphan_notes_success(self, mcp_server):
        """Test getting orphan notes via MCP"""
        args = {
            "limit": 100
        }

        result = await mcp_server.call_tool("get_orphan_notes", args)

        assert len(result) == 1
        assert "orphan notes found" in result[0].text.lower() or "Orphan Notes" in result[0].text


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetNoteGraph:
    """Test MCP get_note_graph tool"""

    async def test_get_note_graph_full(self, mcp_server):
        """Test getting full note graph via MCP"""
        args = {
            "depth": 1,
            "max_nodes": 50
        }

        result = await mcp_server.call_tool("get_note_graph", args)

        assert len(result) == 1
        assert "Knowledge Graph" in result[0].text
        assert "nodes" in result[0].text.lower()

    async def test_get_note_graph_centered(self, mcp_server):
        """Test getting centered graph via MCP"""
        args = {
            "center_note": "Welcome",
            "depth": 1,
            "max_nodes": 50
        }

        result = await mcp_server.call_tool("get_note_graph", args)

        assert "Welcome" in result[0].text


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPDeleteNote:
    """Test MCP delete_note tool"""

    async def test_delete_note_success(self, mcp_server):
        """Test deleting note via MCP"""
        args = {
            "file_path": "Orphan Note.md"
        }

        result = await mcp_server.call_tool("delete_note", args)

        assert "deleted successfully" in result[0].text.lower()

    async def test_delete_note_not_found(self, mcp_server):
        """Test deleting non-existent note via MCP"""
        args = {
            "file_path": "nonexistent.md"
        }

        result = await mcp_server.call_tool("delete_note", args)

        assert "not found" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPMoveNote:
    """Test MCP move_note tool"""

    async def test_move_note_success(self, mcp_server):
        """Test moving note via MCP"""
        args = {
            "old_path": "Orphan Note.md",
            "new_path": "Renamed Note.md"
        }

        result = await mcp_server.call_tool("move_note", args)

        assert "moved successfully" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPResolveWikiLink:
    """Test MCP resolve_wiki_link tool"""

    async def test_resolve_wiki_link_success(self, mcp_server):
        """Test resolving wiki-link via MCP"""
        args = {
            "link_name": "Welcome"
        }

        result = await mcp_server.call_tool("resolve_wiki_link", args)

        assert "Welcome.md" in result[0].text

    async def test_resolve_wiki_link_not_found(self, mcp_server):
        """Test resolving non-existent link via MCP"""
        args = {
            "link_name": "Nonexistent"
        }

        result = await mcp_server.call_tool("resolve_wiki_link", args)

        assert "not found" in result[0].text.lower()


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPGetVaultStats:
    """Test MCP get_vault_stats tool"""

    async def test_get_vault_stats(self, mcp_server):
        """Test getting vault stats via MCP"""
        args = {}

        result = await mcp_server.call_tool("get_vault_stats", args)

        assert len(result) == 1
        assert "Vault Statistics" in result[0].text
        assert "Total notes" in result[0].text


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPListTags:
    """Test MCP list_tags tool"""

    async def test_list_tags(self, mcp_server):
        """Test listing tags via MCP"""
        args = {}

        result = await mcp_server.call_tool("list_tags", args)

        assert len(result) == 1
        assert "tags found" in result[0].text.lower() or "Tags" in result[0].text


@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
class TestMCPToolNotFound:
    """Test MCP error handling"""

    async def test_tool_not_found(self, mcp_server):
        """Test calling non-existent tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await mcp_server.call_tool("nonexistent_tool", {})
