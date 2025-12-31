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
security = HTTPBearer(auto_error=False)  # Don't auto-error, we'll handle it in verify_api_key

# Global vault manager (will be set by main.py)
vault_manager: Optional[VaultManager] = None


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Verify API key from Bearer token (constant-time comparison)"""
    # Skip authentication in dev mode
    if settings.devmode:
        logger.warning("🔓 Dev mode enabled - skipping API key authentication")
        return "dev-mode"
    
    # In production mode, credentials are required
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not secrets.compare_digest(credentials.credentials, settings.mcp_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials


def normalize_tags(tags: List[str]) -> tuple[List[str], List[str]]:
    """
    Normalize tags by removing # prefix if present.

    Frontmatter tags should NOT have # prefix (only inline tags do).

    Args:
        tags: List of tag strings

    Returns:
        Tuple of (normalized_tags, warnings)
    """
    normalized = []
    warnings = []
    for tag in tags:
        if isinstance(tag, str):
            # Remove leading # if present
            normalized_tag = tag.lstrip('#').strip()
            if normalized_tag:  # Only add non-empty tags
                normalized.append(normalized_tag)
                if tag.startswith('#'):
                    warnings.append(f"Normalized '{tag}' to '{normalized_tag}' (frontmatter tags don't use #)")
                    logger.info(f"Normalized tag '{tag}' to '{normalized_tag}' (removed # prefix)")
        else:
            # Non-string tag, keep as-is
            normalized.append(tag)
    return normalized, warnings


def normalize_frontmatter_tags(frontmatter: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    """
    Normalize tags in frontmatter by removing # prefix if present.

    Args:
        frontmatter: Frontmatter dictionary

    Returns:
        Tuple of (frontmatter with normalized tags, list of warnings)
    """
    warnings = []

    if 'tags' not in frontmatter:
        return frontmatter, warnings

    tags = frontmatter['tags']

    # Handle different tag formats
    if isinstance(tags, list):
        normalized_tags, tag_warnings = normalize_tags(tags)
        frontmatter['tags'] = normalized_tags
        warnings.extend(tag_warnings)
    elif isinstance(tags, str):
        # Single tag or comma/space separated
        # Remove # prefix and split
        normalized = tags.lstrip('#').strip()
        frontmatter['tags'] = [normalized] if normalized else []
        if tags.startswith('#'):
            warnings.append(f"Normalized '{tags}' to '{normalized}' (frontmatter tags don't use #)")
            logger.info(f"Normalized tag string '{tags}' to '{normalized}'")

    return frontmatter, warnings


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


class GetBacklinksRequest(BaseModel):
    title: str


class GetOrphanNotesRequest(BaseModel):
    limit: int = 100


class GetNoteGraphRequest(BaseModel):
    center_note: Optional[str] = None
    depth: int = 1
    max_nodes: int = 50


class GetTableOfContentsRequest(BaseModel):
    path: str
    max_depth: int = 6


class ReadSectionRequest(BaseModel):
    path: str
    section_ref: str


class ReadBlockRequest(BaseModel):
    path: str
    block_id: str


class UpdateSectionRequest(BaseModel):
    path: str
    section_ref: str
    new_content: str


class UpdateBlockRequest(BaseModel):
    path: str
    block_id: str
    new_content: str


# Create router
router = APIRouter(prefix="/tools", tags=["Obsidian Tools"])


@router.post("/create_note", dependencies=[Security(verify_api_key)])
async def create_note(request: CreateNoteRequest):
    """
    Create a brand new note in the vault with title, content, and tags.

    Use this tool when:
    - User asks to "create a new note" or "make a note about..."
    - You need to create a new document from scratch
    - User wants to save/store new information

    DO NOT use this when:
    - The note already exists - use update_note or add_to_note instead
    - You want to add to an existing note - use add_to_note instead

    The note will be created with:
    - Frontmatter containing title and optional tags
    - The specified content as the body
    - Filename based on the title (e.g., "My Note" → "My Note.md")
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        # Build frontmatter
        frontmatter = {"title": request.title}
        warnings = []

        if request.tags:
            # Normalize tags (remove # prefix if present)
            normalized_tags, tag_warnings = normalize_tags(request.tags)
            frontmatter["tags"] = normalized_tags
            warnings.extend(tag_warnings)

        # Create note (title will be used as filename)
        note = vault_manager.create_note(
            path=f"{request.title}.md",
            content=request.content,
            frontmatter=frontmatter
        )

        # Include warnings in response if any
        response = {
            "success": True,
            "note": note
        }
        if warnings:
            response["tag_normalization_warnings"] = warnings

        return response
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
        warnings = []
        frontmatter = request.frontmatter

        # Normalize tags in frontmatter (remove # prefix if present)
        if frontmatter and 'tags' in frontmatter:
            frontmatter, tag_warnings = normalize_frontmatter_tags(frontmatter)
            warnings.extend(tag_warnings)

        note = vault_manager.update_note(
            path=request.file_path,
            content=request.content,
            frontmatter=frontmatter,
            append=request.append
        )

        # Include warnings in response if any
        response = {
            "success": True,
            "note": note
        }
        if warnings:
            response["tag_normalization_warnings"] = warnings

        return response
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
    """
    Search notes by content and tags with optional regex support.

    Use this tool when:
    - You need to FIND notes containing specific text/keywords
    - You want to search across multiple notes
    - You need to filter by tags

    DO NOT use this tool when:
    - You want to READ a specific section - use read_section instead
    - You know the exact note and section you want - use read_section instead

    Returns: List of matching notes with excerpts showing where the search term appears
    """
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
    """
    List all notes in the vault or a specific directory with metadata.

    Use this tool when:
    - User asks "what notes do I have?" or "list all notes"
    - You need to see available notes in a folder
    - You want to get an overview of the vault structure
    - You need to see recently modified notes (use sort_by: "modified")

    DO NOT use this when:
    - You want to FIND notes with specific content - use search_notes instead
    - You already know the note name - use get_note_by_title instead

    Returns: List of notes with paths, titles, size, modified dates, and optionally frontmatter
    """
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
    """
    Get the complete content of a note by its title.

    Use this tool when:
    - You know the exact note title/name
    - You want to read the ENTIRE note content
    - User asks "show me [note name]" or "read [note name]"

    DO NOT use this when:
    - You only want a specific section - use read_section instead
    - You want to find notes - use search_notes instead
    - You only need metadata - use get_note_metadata instead

    Returns: Full note content including frontmatter and body
    """
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


@router.post("/get_backlinks", dependencies=[Security(verify_api_key)])
async def get_backlinks(request: GetBacklinksRequest):
    """Get all notes that link to (reference) a specific note"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.get_backlinks(request.title)

        return {
            "success": True,
            "backlinks": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting backlinks", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get backlinks")


@router.post("/get_orphan_notes", dependencies=[Security(verify_api_key)])
async def get_orphan_notes(request: GetOrphanNotesRequest):
    """Find notes with no backlinks (orphaned/isolated notes)"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        orphans = vault_manager.get_orphan_notes(request.limit)

        return {
            "success": True,
            "orphans": orphans,
            "count": len(orphans)
        }
    except Exception as e:
        logger.error(f"Error getting orphan notes", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get orphan notes")


@router.post("/get_note_graph", dependencies=[Security(verify_api_key)])
async def get_note_graph(request: GetNoteGraphRequest):
    """Get a knowledge graph of notes and their connections"""
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        graph = vault_manager.get_note_graph(
            center_note=request.center_note,
            depth=request.depth,
            max_nodes=request.max_nodes
        )

        return {
            "success": True,
            "graph": graph
        }
    except Exception as e:
        logger.error(f"Error getting note graph", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get note graph")


@router.post("/get_table_of_contents", dependencies=[Security(verify_api_key)])
async def get_table_of_contents(request: GetTableOfContentsRequest):
    """
    Get hierarchical table of contents from a note showing all section headings.

    Use this tool when:
    - You need to see what sections/headings exist in a note
    - You want to understand the structure of a document
    - You need section names before reading specific sections
    - User asks "what sections are in..." or "show me the structure of..."

    Returns: List of headings with their levels, anchors, and metadata (word count, reading time)
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.get_table_of_contents(
            path=request.path,
            max_depth=request.max_depth
        )

        return {
            "success": True,
            "toc": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting table of contents", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get table of contents")


@router.post("/read_section", dependencies=[Security(verify_api_key)])
async def read_section(request: ReadSectionRequest):
    """
    Read the full content of a specific section from a note by heading name.

    Use this tool when:
    - You need to read a specific section's content (e.g., "What does section X say?")
    - You want the complete text under a particular heading
    - You know which section/heading you want to read

    The heading reference supports fuzzy matching:
    - Case-insensitive
    - Ignores markdown formatting (**, *, ~~)
    - Ignores trailing punctuation (:, ., !, ?)

    Examples:
    - "Multi-tenant tends to win when" matches "**Multi-tenant tends to win when:**"
    - "Where each architecture wins" matches "**Where each architecture tends to win**"
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.read_section(
            path=request.path,
            section_ref=request.section_ref
        )

        return {
            "success": True,
            "section": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading section", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read section")


@router.post("/read_block", dependencies=[Security(verify_api_key)])
async def read_block(request: ReadBlockRequest):
    """
    Read a specific block from a note by its block ID (^block-id).

    Blocks are paragraphs, lists, quotes, or code blocks marked with ^block-id at the end.
    Example: "This is a paragraph. ^intro" - block_id is "intro"

    Use this tool when:
    - User references a specific block ID (e.g., "read block intro")
    - You see ^block-id markers in the note and need to read that specific block
    - You need precise paragraph/list-level content, not entire sections

    DO NOT use this when:
    - You want to read by heading - use read_section instead
    - The note doesn't have block IDs - use read_section or get_note_by_title instead

    Note: Block IDs are manually added by users with ^id syntax, not auto-generated
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.read_block(
            path=request.path,
            block_id=request.block_id
        )

        return {
            "success": True,
            "block": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reading block", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read block")


@router.post("/update_section", dependencies=[Security(verify_api_key)])
async def update_section(request: UpdateSectionRequest):
    """
    Update the content of a specific section (by heading name) in a note.

    Use this tool when:
    - You need to replace the content under a specific heading
    - User asks to "update the [section name] section"
    - You want to rewrite content organized by heading structure

    The heading reference supports fuzzy matching (same as read_section).

    DO NOT use this when:
    - You want to add to the end of the note - use add_to_note instead
    - You want to replace the entire note - use update_note instead
    - You want to update a specific block by ID - use update_block instead

    Note: This replaces the section content, keeping the heading intact
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.update_section(
            path=request.path,
            section_ref=request.section_ref,
            new_content=request.new_content
        )

        return {
            "success": True,
            "note": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating section", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update section")


@router.post("/update_block", dependencies=[Security(verify_api_key)])
async def update_block(request: UpdateBlockRequest):
    """
    Update a specific block (paragraph, list, quote) by its block ID (^block-id).

    Use this tool when:
    - You need to update content marked with a specific ^block-id
    - User asks to "update block [id]"
    - You want precise paragraph/list-level updates

    DO NOT use this when:
    - You want to update by heading - use update_section instead
    - The note doesn't have block IDs - use update_section or update_note instead
    - You want to add content to the end - use add_to_note instead

    Note: The new_content should include the ^block-id marker at the end if you want to preserve it
    """
    if vault_manager is None:
        raise HTTPException(status_code=503, detail="Vault manager not initialized")

    try:
        result = vault_manager.update_block(
            path=request.path,
            block_id=request.block_id,
            new_content=request.new_content
        )

        return {
            "success": True,
            "note": result
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating block", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update block")


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


# ==================== Template Endpoints ====================

class CreateFromTemplateRequest(BaseModel):
    template_name: str
    note_path: str
    variables: Optional[Dict[str, str]] = None
    frontmatter: Optional[Dict[str, Any]] = None


class SaveTemplateRequest(BaseModel):
    template_name: str
    content: str


@router.post("/list_templates", dependencies=[Security(verify_api_key)])
async def list_templates():
    """
    List all available templates in the .templates/ folder.

    Use this tool when:
    - You want to see what templates are available
    - You need to know what variables a template expects
    - User asks "what templates exist" or "show me the templates"

    Returns: List of template metadata including name, variables, extends, and includes
    """
    try:
        result = vault_manager.list_templates()

        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"Error listing templates", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.post("/create_from_template", dependencies=[Security(verify_api_key)])
async def create_from_template(request: CreateFromTemplateRequest):
    """
    Create a new note from a template with variable substitution.

    Use this tool when:
    - You want to create a note using a predefined template
    - You need consistent note structure (e.g., meeting notes, project plans)
    - User asks to "create a note from template X"

    Templates support:
    - Variable substitution: {{variable_name}}
    - Built-in macros: {{date}}, {{time}}, {{datetime}}, {{date:%Y-%m-%d}}
    - Template inheritance: {% extends "base" %}
    - Template includes: {% include "header" %}

    Example variables:
    {
      "project_name": "My Project",
      "author": "John Doe",
      "priority": "high"
    }

    Returns: Created note metadata with path, size, and status
    """
    try:
        result = vault_manager.create_from_template(
            template_name=request.template_name,
            note_path=request.note_path,
            variables=request.variables,
            frontmatter=request.frontmatter
        )

        return {
            "success": True,
            **result
        }
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating note from template", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create note from template: {str(e)}")


@router.post("/save_template", dependencies=[Security(verify_api_key)])
async def save_template(request: SaveTemplateRequest):
    """
    Save a template to the .templates/ folder for future reuse.

    Use this tool when:
    - You want to save a note structure as a template
    - You need to create reusable note formats
    - User asks to "save this as a template" or "create a template"

    Template syntax:
    - Variables: {{variable_name}}
    - Date macro: {{date}} or {{date:%Y-%m-%d}}
    - Time macro: {{time}}
    - Datetime macro: {{datetime}}
    - Extends: {% extends "base_template" %}
    - Include: {% include "header_template" %}

    Example template content:
    ```markdown
    ---
    title: {{project_name}}
    author: {{author}}
    created: {{date}}
    ---

    # {{project_name}}

    ## Overview
    [Your overview here]

    ## Timeline
    Created: {{datetime}}
    ```

    Returns: Template metadata including name, variables, and file path
    """
    try:
        result = vault_manager.save_template(
            template_name=request.template_name,
            content=request.content
        )

        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving template", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")
