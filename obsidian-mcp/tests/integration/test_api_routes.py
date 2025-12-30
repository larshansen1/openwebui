"""
Integration tests for REST API endpoints (app/api/routes.py)
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.main import app
from app.api import routes as api_routes
from app.config import settings


@pytest.fixture
def client(vault_manager):
    """Create TestClient with vault manager"""
    # Set vault manager for API routes
    api_routes.vault_manager = vault_manager

    # Create test client
    return TestClient(app)


@pytest.fixture
def test_api_key():
    """Test API key"""
    return settings.mcp_api_key


@pytest.fixture
def headers(test_api_key):
    """Authentication headers"""
    return {"Authorization": f"Bearer {test_api_key}"}


@pytest.mark.integration
@pytest.mark.api
class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_health_check(self, client):
        """Test health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "vault" in data
        assert "total_notes" in data["vault"]

    def test_vault_stats_authenticated(self, client, headers):
        """Test vault stats with authentication"""
        response = client.get("/vault/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_notes" in data
        assert "vault_path" in data

    def test_vault_stats_unauthenticated(self, client):
        """Test vault stats without authentication"""
        response = client.get("/vault/stats")

        assert response.status_code == 403  # Forbidden


@pytest.mark.integration
@pytest.mark.api
class TestCreateNote:
    """Test create_note endpoint"""

    def test_create_note_success(self, client, headers):
        """Test creating a note successfully"""
        payload = {
            "title": "API Test Note",
            "content": "Test content from API",
            "tags": ["api", "test"]
        }

        response = client.post("/tools/create_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["note"]["title"] == "API Test Note"
        assert "api" in data["note"]["tags"]

    def test_create_note_duplicate(self, client, headers):
        """Test creating duplicate note"""
        payload = {
            "title": "Welcome",
            "content": "Duplicate",
            "tags": []
        }

        response = client.post("/tools/create_note", json=payload, headers=headers)

        assert response.status_code == 409  # Conflict

    def test_create_note_unauthenticated(self, client):
        """Test creating note without authentication"""
        payload = {
            "title": "Test",
            "content": "Content",
            "tags": []
        }

        response = client.post("/tools/create_note", json=payload)

        assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.api
class TestUpdateNote:
    """Test update_note endpoint"""

    def test_update_note_content(self, client, headers):
        """Test updating note content"""
        payload = {
            "file_path": "Welcome.md",
            "content": "Updated content via API"
        }

        response = client.post("/tools/update_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["note"]["content"] == "Updated content via API"

    def test_update_note_frontmatter(self, client, headers):
        """Test updating note frontmatter"""
        payload = {
            "file_path": "Welcome.md",
            "frontmatter": {
                "title": "Welcome",
                "new_field": "test_value"
            }
        }

        response = client.post("/tools/update_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["note"]["frontmatter"]["new_field"] == "test_value"

    def test_update_note_not_found(self, client, headers):
        """Test updating non-existent note"""
        payload = {
            "file_path": "nonexistent.md",
            "content": "New content"
        }

        response = client.post("/tools/update_note", json=payload, headers=headers)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
class TestAppendToNote:
    """Test add_to_note (append) endpoint"""

    def test_append_to_note_success(self, client, headers):
        """Test appending content to note"""
        payload = {
            "file_path": "Welcome.md",
            "content": "Appended content"
        }

        response = client.post("/tools/add_to_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Appended content" in data["note"]["content"]

    def test_append_empty_content(self, client, headers):
        """Test appending empty content"""
        payload = {
            "file_path": "Welcome.md",
            "content": ""
        }

        response = client.post("/tools/add_to_note", json=payload, headers=headers)

        assert response.status_code == 400  # Bad request

    def test_append_to_nonexistent(self, client, headers):
        """Test appending to non-existent note"""
        payload = {
            "file_path": "nonexistent.md",
            "content": "New content"
        }

        response = client.post("/tools/add_to_note", json=payload, headers=headers)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
class TestMoveNote:
    """Test move_note endpoint"""

    def test_move_note_success(self, client, headers):
        """Test moving/renaming a note"""
        payload = {
            "old_path": "Orphan Note.md",
            "new_path": "Renamed Note.md"
        }

        response = client.post("/tools/move_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Renamed Note.md" in data["note"]["path"]

    def test_move_note_to_existing(self, client, headers):
        """Test moving to existing destination"""
        payload = {
            "old_path": "Orphan Note.md",
            "new_path": "Welcome.md"
        }

        response = client.post("/tools/move_note", json=payload, headers=headers)

        assert response.status_code == 409  # Conflict


@pytest.mark.integration
@pytest.mark.api
class TestDeleteNote:
    """Test delete_note endpoint"""

    def test_delete_note_success(self, client, headers):
        """Test deleting a note"""
        payload = {
            "file_path": "Orphan Note.md"
        }

        response = client.post("/tools/delete_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_note_not_found(self, client, headers):
        """Test deleting non-existent note"""
        payload = {
            "file_path": "nonexistent.md"
        }

        response = client.post("/tools/delete_note", json=payload, headers=headers)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
class TestSearchNotes:
    """Test search_notes endpoint"""

    def test_search_basic(self, client, headers):
        """Test basic search"""
        payload = {
            "query": "vault",
            "limit": 50,
            "use_regex": False
        }

        response = client.post("/tools/search_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) > 0

    def test_search_with_tags(self, client, headers):
        """Test search with tag filter"""
        payload = {
            "query": "",
            "tags": ["meta"],
            "limit": 50,
            "use_regex": False
        }

        response = client.post("/tools/search_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

    def test_search_with_regex(self, client, headers):
        """Test search with regex"""
        payload = {
            "query": r"\[\[.*?\]\]",
            "limit": 50,
            "use_regex": True
        }

        response = client.post("/tools/search_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0


@pytest.mark.integration
@pytest.mark.api
class TestListNotes:
    """Test list_notes endpoint"""

    def test_list_all_notes(self, client, headers):
        """Test listing all notes"""
        payload = {
            "directory": "",
            "recursive": True,
            "include_frontmatter": False,
            "limit": 100,
            "offset": 0,
            "sort_by": "modified"
        }

        response = client.post("/tools/list_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["notes"]) > 0

    def test_list_with_sort_by_title(self, client, headers):
        """Test listing with title sort"""
        payload = {
            "sort_by": "title",
            "limit": 100,
            "recursive": True
        }

        response = client.post("/tools/list_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        titles = [n["title"] for n in data["notes"]]
        assert titles == sorted(titles)


@pytest.mark.integration
@pytest.mark.api
class TestGetNoteByTitle:
    """Test get_note_by_title endpoint"""

    def test_get_note_by_title_success(self, client, headers):
        """Test getting note by title"""
        payload = {
            "title": "Welcome"
        }

        response = client.post("/tools/get_note_by_title", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["note"]["title"] == "Welcome"

    def test_get_note_by_title_not_found(self, client, headers):
        """Test getting non-existent note"""
        payload = {
            "title": "Nonexistent"
        }

        response = client.post("/tools/get_note_by_title", json=payload, headers=headers)

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
class TestGetNoteMetadata:
    """Test get_note_metadata endpoint"""

    def test_get_metadata_success(self, client, headers):
        """Test getting note metadata"""
        payload = {
            "title": "Welcome"
        }

        response = client.post("/tools/get_note_metadata", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["title"] == "Welcome"
        assert "content" not in data["metadata"]  # Should not include full content


@pytest.mark.integration
@pytest.mark.api
class TestGetDailyNote:
    """Test get_daily_note endpoint"""

    def test_get_daily_note_today(self, client, headers):
        """Test getting today's daily note"""
        payload = {}

        response = client.post("/tools/get_daily_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "daily-note" in data["note"]["tags"]

    def test_get_daily_note_specific_date(self, client, headers):
        """Test getting daily note for specific date"""
        payload = {
            "date": "2025-01-01"
        }

        response = client.post("/tools/get_daily_note", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["note"]["title"] == "2025-01-01"

    def test_get_daily_note_invalid_date(self, client, headers):
        """Test getting daily note with invalid date"""
        payload = {
            "date": "invalid"
        }

        response = client.post("/tools/get_daily_note", json=payload, headers=headers)

        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.api
class TestGetBacklinks:
    """Test get_backlinks endpoint"""

    def test_get_backlinks_success(self, client, headers):
        """Test getting backlinks"""
        payload = {
            "title": "Projects"
        }

        response = client.post("/tools/get_backlinks", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "backlinks" in data


@pytest.mark.integration
@pytest.mark.api
class TestGetOrphanNotes:
    """Test get_orphan_notes endpoint"""

    def test_get_orphan_notes_success(self, client, headers):
        """Test getting orphan notes"""
        payload = {
            "limit": 100
        }

        response = client.post("/tools/get_orphan_notes", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "orphans" in data


@pytest.mark.integration
@pytest.mark.api
class TestGetNoteGraph:
    """Test get_note_graph endpoint"""

    def test_get_note_graph_full(self, client, headers):
        """Test getting full note graph"""
        payload = {
            "depth": 1,
            "max_nodes": 50
        }

        response = client.post("/tools/get_note_graph", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]

    def test_get_note_graph_centered(self, client, headers):
        """Test getting graph centered on note"""
        payload = {
            "center_note": "Welcome",
            "depth": 1,
            "max_nodes": 50
        }

        response = client.post("/tools/get_note_graph", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["graph"]["nodes"]) > 0


@pytest.mark.integration
@pytest.mark.api
class TestListTags:
    """Test list_tags endpoint"""

    def test_list_tags(self, client, headers):
        """Test listing all tags"""
        response = client.get("/tools/list_tags", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "tags" in data
        assert "total_unique_tags" in data


@pytest.mark.integration
@pytest.mark.api
class TestResolveWikiLink:
    """Test resolve_wiki_link endpoint"""

    def test_resolve_wiki_link_success(self, client, headers):
        """Test resolving wiki-link"""
        payload = {
            "link_name": "Welcome"
        }

        response = client.post("/tools/resolve_wiki_link", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["file_path"] == "Welcome.md"

    def test_resolve_wiki_link_not_found(self, client, headers):
        """Test resolving non-existent link"""
        payload = {
            "link_name": "Nonexistent"
        }

        response = client.post("/tools/resolve_wiki_link", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
