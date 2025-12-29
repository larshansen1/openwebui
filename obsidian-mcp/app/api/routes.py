"""
REST API routes for Obsidian vault operations
Exposes MCP tools as HTTP endpoints for Open WebUI integration
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import secrets

from app.config import settings
from app.vault.manager import VaultManager

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Global vault manager (will be set by main.py)
vault_manager: Optional[VaultManager] = None


def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify API key from Bearer token (constant-time comparison)"""
    if not secrets.compare_digest(credentials.credentials, settings.mcp_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


# Request/Response models
class CreateNoteRequest(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None


class UpdateNoteRequest(BaseModel):
    file_path: str
    content: Optional[str] = None
    frontmatter: Optional[Dict[str, Any]] = None
    append: bool = False


class MoveNoteRequest(BaseModel):
    old_path: str
    new_path: str


class DeleteNoteRequest(BaseModel):
    file_path: str


class AppendToNoteRequest(BaseModel):
    file_path: str
    content: str  # Required for append


class SearchNotesRequest(BaseModel):
    query: str
    tags: Optional[List[str]] = None
    limit: int = 50
    use_regex: bool = False


class ListNotesRequest(BaseModel):
    directory: str = ""
    recursive: bool = True
    include_frontmatter: bool = False
    limit: int = 100
    offset: int = 0
    sort_by: str = "modified"


class GetNoteByTitleRequest(BaseModel):
    title: str


class ResolveWikiLinkRequest(BaseModel):
    link_name: str


class GetNoteMetadataRequest(BaseModel):
    title: str


class GetDailyNoteRequest(BaseModel):
    date: Optional[str] = None


# Create router
router = APIRouter(prefix="/tools", tags=["Obsidian Tools"])


@router.post("/create_note", dependencies=[Security(verify_api_key)])
async def create_note(request: CreateNoteRequest):
    """Create a new note in the vault"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        # Build frontmatter
        frontmatter = {"title": request.title}
        if request.tags:
            frontmatter["tags"] = request.tags

        # Create note (title will be used as filename)
        note = vault_manager.create_note(
            path=f"{request.title}.md",
            content=request.content,
            frontmatter=frontmatter
        )

        return {
            "success": True,
            "note": note
        }
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create note")


@router.post("/update_note", dependencies=[Security(verify_api_key)])
async def update_note(request: UpdateNoteRequest):
    """Update note content or frontmatter (use append_to_note for adding content to end)

    This tool is for replacing content or updating frontmatter.
    To ADD content to the end of a note, use append_to_note instead.
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        note = vault_manager.update_note(
            path=request.file_path,
            content=request.content,
            frontmatter=request.frontmatter,
            append=request.append
        )

        return {
            "success": True,
            "note": note
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update note")


@router.post("/move_note", dependencies=[Security(verify_api_key)])
async def move_note(request: MoveNoteRequest):
    """Move or rename a note"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        note = vault_manager.move_note(
            old_path=request.old_path,
            new_path=request.new_path
        )

        return {
            "success": True,
            "note": note,
            "message": f"Note moved: {request.old_path} → {note['path']}"
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Error moving note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to move note")


@router.post("/delete_note", dependencies=[Security(verify_api_key)])
async def delete_note(request: DeleteNoteRequest):
    """Delete a note"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        vault_manager.delete_note(path=request.file_path)

        return {
            "success": True,
            "message": f"Note deleted: {request.file_path}"
        }
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete note")


@router.post("/add_to_note", dependencies=[Security(verify_api_key)])
async def add_to_note(request: AppendToNoteRequest):
    """Add new content to the end of an existing note

    Use this tool to add content to an existing note without replacing it.
    The new content will be added after two newlines. This is the recommended method
    for adding remarks, sections, or updates to notes.

    Example usage:
    - Adding a new section to a note
    - Adding a remark or comment
    - Adding follow-up information
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    if not request.content or request.content.strip() == "":
        raise HTTPException(status_code=400, detail="Content is required for append and cannot be empty")

    # Debug logging to see what content is being received
    logger.info(f"append_to_note called: path={request.file_path}, content_length={len(request.content)}")
    logger.debug(f"Content preview: {request.content[:200]}...")

    try:
        note = vault_manager.update_note(
            path=request.file_path,
            content=request.content,
            append=True
        )

        return {
            "success": True,
            "note": note
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error appending to note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to append to note")


@router.post("/search_notes", dependencies=[Security(verify_api_key)])
async def search_notes(request: SearchNotesRequest):
    """Search notes by content and tags with optional regex support"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        results = vault_manager.search_notes(
            query=request.query,
            tags=request.tags,
            limit=request.limit,
            use_regex=request.use_regex
        )

        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error searching notes", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search notes")


@router.post("/list_notes", dependencies=[Security(verify_api_key)])
async def list_notes(request: ListNotesRequest):
    """List all notes in the vault with optional sorting"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        notes = vault_manager.list_notes(
            directory=request.directory,
            recursive=request.recursive,
            include_frontmatter=request.include_frontmatter,
            limit=request.limit,
            offset=request.offset,
            sort_by=request.sort_by
        )

        return {
            "success": True,
            "notes": notes,
            "count": len(notes)
        }
    except Exception as e:
        logger.error(f"Error listing notes", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list notes")


@router.post("/get_note_by_title", dependencies=[Security(verify_api_key)])
async def get_note_by_title(request: GetNoteByTitleRequest):
    """Get a note by its title"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        # Resolve title to file path
        file_path = vault_manager.parser.resolve_wiki_link(request.title)

        if not file_path:
            raise HTTPException(status_code=404, detail=f"Note not found: {request.title}")

        # Read the note
        note = vault_manager.read_note(file_path)

        return {
            "success": True,
            "note": note
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is (don't convert to 500)
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting note by title", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get note")


@router.post("/resolve_wiki_link", dependencies=[Security(verify_api_key)])
async def resolve_wiki_link(request: ResolveWikiLinkRequest):
    """Resolve a wiki-link to a file path"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        file_path = vault_manager.parser.resolve_wiki_link(request.link_name)

        if not file_path:
            return {
                "success": False,
                "message": f"Wiki link not found: {request.link_name}",
                "file_path": None
            }

        return {
            "success": True,
            "file_path": file_path,
            "link_name": request.link_name
        }
    except Exception as e:
        logger.error(f"Error resolving wiki link", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resolve wiki link")


@router.post("/get_note_metadata", dependencies=[Security(verify_api_key)])
async def get_note_metadata(request: GetNoteMetadataRequest):
    """Get only the metadata/frontmatter of a note without full content"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        metadata = vault_manager.get_note_metadata(request.title)

        return {
            "success": True,
            "metadata": metadata
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting note metadata", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get note metadata")


@router.post("/get_daily_note", dependencies=[Security(verify_api_key)])
async def get_daily_note(request: GetDailyNoteRequest):
    """Get or create a daily note for a specific date"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        note = vault_manager.get_daily_note(request.date)

        return {
            "success": True,
            "note": note
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting daily note", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get daily note")


@router.get("/list_tags", dependencies=[Security(verify_api_key)])
async def list_tags():
    """List all tags in the vault with usage counts"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        # Collect all tags from all notes
        tag_counts: Dict[str, int] = {}

        for md_file in vault_manager.vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                metadata, body = vault_manager.parser.parse_note(content)
                tags = vault_manager.parser.extract_tags(metadata, body)

                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                continue

        # Sort by usage count (descending)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "success": True,
            "tags": [{"tag": tag, "count": count} for tag, count in sorted_tags],
            "total_unique_tags": len(sorted_tags)
        }
    except Exception as e:
        logger.error(f"Error listing tags", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list tags")
