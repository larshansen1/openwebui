# Obsidian MCP Server - Changelog

## 2025-12-29 - Added Move/Rename Functionality

### New Features

#### `move_note` Tool
- **Function**: Move or rename notes to new locations within the vault
- **Parameters**:
  - `old_path` (string, required): Current relative path to the note
  - `new_path` (string, required): New relative path (can include subdirectories like 'folder/subfolder/name')
- **Returns**: Updated note data at the new location
- **Behavior**:
  - Automatically creates parent directories if they don't exist
  - Preserves file metadata (creation time, modification time)
  - Automatically adds `.md` extension if missing
  - Maintains all frontmatter and content
  - Updates vault cache and title mappings
  - Atomic operation (uses `rename()` system call)

### Usage Examples

**Simple Rename:**
```json
{
  "old_path": "My Note.md",
  "new_path": "Renamed Note"
}
```

**Move to Subfolder:**
```json
{
  "old_path": "My Note.md",
  "new_path": "tech/programming/My Note"
}
```

**Move and Rename:**
```json
{
  "old_path": "quick-notes/Draft.md",
  "new_path": "articles/published/Final Article"
}
```

### API Endpoint

**HTTP REST API:**
```bash
POST /tools/move_note
Authorization: Bearer <MCP_API_KEY>
Content-Type: application/json

{
  "old_path": "source/path.md",
  "new_path": "destination/path"
}
```

**Response:**
```json
{
  "success": true,
  "note": {
    "path": "destination/path.md",
    "name": "path",
    "content": "...",
    "frontmatter": {...},
    "tags": [...],
    ...
  },
  "message": "Note moved: source/path.md → destination/path.md"
}
```

### Error Handling

- **FileNotFoundError (404)**: Source note doesn't exist
- **FileExistsError (409)**: Destination path already exists
- **ValueError (400)**: Invalid path (path traversal, symlinks, etc.)

### Technical Details

- Implemented in `app/vault/manager.py:move_note()`
- Exposed via MCP protocol in `app/mcp/server.py`
- HTTP endpoint in `app/api/routes.py`
- Uses Python's `Path.rename()` for atomic file system operations
- Full path validation with security checks (prevents path traversal attacks)

---

## Previous Functionality

### Available Tools (Before This Update)
1. `create_note` - Create new notes
2. `read_note` - Read note content
3. `update_note` - Update note content and frontmatter
4. `delete_note` - Delete notes
5. `append_to_note` - Append content to notes
6. `search_notes` - Search by content and tags
7. `list_notes` - List notes with filtering
8. `get_note_by_title` - Find notes by title
9. `resolve_wiki_link` - Resolve [[wiki-links]]
10. `list_tags` - List all tags with usage counts

### Now Available
✅ **11. `move_note` - Move/rename notes** (NEW)
