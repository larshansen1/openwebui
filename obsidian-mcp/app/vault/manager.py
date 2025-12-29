"""
Vault Manager - Core CRUD operations for Obsidian vault
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.vault.parser import MarkdownParser
from app.vault.cache import SimpleCache

logger = logging.getLogger(__name__)


class VaultManager:
    """Manages all vault operations"""

    def __init__(self):
        """Initialize vault manager"""
        self.vault_path = settings.vault_path
        self.parser = MarkdownParser(self.vault_path)
        self.cache = SimpleCache(
            max_size=settings.cache_max_size,
            default_ttl=settings.cache_ttl_seconds
        )
        logger.info(f"VaultManager initialized with vault: {self.vault_path}")

    def _normalize_path_case(self, path: str) -> str:
        """
        Normalize path to lowercase if configured (for cross-platform syncing)

        Only lowercases directory components, preserves filename case for readability.
        Example: "Tech/Projects/Meeting Notes.md" → "tech/projects/Meeting Notes.md"

        Args:
            path: Path to normalize

        Returns:
            Normalized path with lowercase directories, original filename
        """
        if settings.normalize_paths_lowercase:
            path_obj = Path(path)

            # Split into directory parts and filename
            if len(path_obj.parts) > 1:
                # Has directory components
                directory_parts = path_obj.parts[:-1]  # All but last
                filename = path_obj.parts[-1]  # Last part (filename)

                # Lowercase only directory parts, preserve filename
                normalized_dirs = "/".join(part.lower() for part in directory_parts)
                normalized = f"{normalized_dirs}/{filename}"
            else:
                # No directory, just filename - preserve as-is
                normalized = path

            if normalized != path:
                logger.debug(f"Normalized path: {path} → {normalized}")
            return normalized
        return path

    def _get_safe_path(self, relative_path: str) -> Path:
        """
        Get safe absolute path, preventing path traversal and symlink attacks

        Args:
            relative_path: Relative path from vault root

        Returns:
            Absolute path within vault

        Raises:
            ValueError: If path escapes vault or contains symlinks
        """
        # Normalize case if configured
        relative_path = self._normalize_path_case(relative_path)

        # Build path without resolving symlinks
        full_path = self.vault_path / relative_path

        # Check for symlinks in the path components
        current = full_path
        while current != self.vault_path:
            if current.is_symlink():
                logger.warning(f"Symlink access attempt blocked: {relative_path}")
                raise ValueError("Invalid path: symlinks not allowed")
            current = current.parent
            if not str(current).startswith(str(self.vault_path)):
                break

        # Resolve and normalize
        resolved_vault = self.vault_path.resolve()
        resolved_path = full_path.resolve()

        # Ensure resolved path is still within vault
        try:
            resolved_path.relative_to(resolved_vault)
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {relative_path}")
            raise ValueError("Invalid path: access denied")

        return resolved_path

    def list_notes(
        self,
        directory: str = "",
        recursive: bool = True,
        include_frontmatter: bool = False,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List notes in vault

        Args:
            directory: Subdirectory to list (empty = root)
            recursive: Whether to recurse into subdirectories
            include_frontmatter: Whether to include full frontmatter
            limit: Maximum results
            offset: Results offset for pagination

        Returns:
            List of note metadata dicts
        """
        cache_key = f"list:{directory}:{recursive}:{include_frontmatter}:{limit}:{offset}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        search_path = self.vault_path if not directory else self._get_safe_path(directory)

        pattern = "**/*.md" if recursive else "*.md"
        files = sorted(search_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

        notes = []
        for md_file in files[offset:offset + limit]:
            try:
                rel_path = str(md_file.relative_to(self.vault_path))
                stat = md_file.stat()

                note_info = {
                    "path": rel_path,
                    "name": md_file.stem,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }

                if include_frontmatter:
                    content = md_file.read_text(encoding='utf-8')
                    metadata, _ = self.parser.parse_note(content)
                    note_info["frontmatter"] = metadata
                    note_info["tags"] = self.parser.extract_tags(metadata, "")

                notes.append(note_info)
            except Exception as e:
                logger.warning(f"Error processing file during list_notes", exc_info=True)
                continue

        self.cache.set(cache_key, notes)
        return notes

    def read_note(self, path: str) -> Dict[str, Any]:
        """
        Read note content and metadata

        Args:
            path: Relative path to note

        Returns:
            Dict with note data

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        cache_key = f"note:{path}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        full_path = self._get_safe_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        if not full_path.suffix == ".md":
            raise ValueError("Only .md files are supported")

        # Check file size
        size = full_path.stat().st_size
        if size > settings.max_file_size_bytes:
            raise ValueError(f"File exceeds max size: {size / 1024 / 1024:.2f}MB")

        # Read and parse
        content = full_path.read_text(encoding='utf-8')
        metadata, body = self.parser.parse_note(content)

        # Extract tags
        tags = self.parser.extract_tags(metadata, body)

        # Extract and resolve wiki-links
        wiki_links = self.parser.extract_wiki_links(body)
        resolved_links = self.parser.resolve_all_links(body)

        stat = full_path.stat()
        result = {
            "path": path,
            "name": full_path.stem,
            "content": body,
            "frontmatter": metadata,
            "tags": tags,
            "wiki_links": wiki_links,
            "resolved_links": resolved_links,
            "size": size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

        self.cache.set(cache_key, result)
        return result

    def create_note(
        self,
        path: str,
        content: str,
        frontmatter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new note

        Args:
            path: Relative path for new note
            content: Note content
            frontmatter: Optional frontmatter metadata

        Returns:
            Created note data

        Raises:
            FileExistsError: If note already exists
        """
        full_path = self._get_safe_path(path)

        if full_path.exists():
            raise FileExistsError(f"Note already exists: {path}")

        # Ensure .md extension
        if not path.endswith('.md'):
            path = f"{path}.md"
            full_path = self._get_safe_path(path)

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Add creation timestamp to frontmatter if not present
        if frontmatter is None:
            frontmatter = {}

        if 'created' not in frontmatter:
            frontmatter['created'] = datetime.now().isoformat()

        # Format content with frontmatter
        full_content = self.parser.format_content_with_frontmatter(content, frontmatter)

        # Write file
        full_path.write_text(full_content, encoding='utf-8')

        logger.info(f"Created note: {path}")

        # Invalidate caches
        self.cache.invalidate_pattern("list:")
        self.parser.invalidate_title_map()

        return self.read_note(path)

    def update_note(
        self,
        path: str,
        content: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        append: bool = False
    ) -> Dict[str, Any]:
        """
        Update existing note

        Args:
            path: Relative path to note
            content: New content (None = keep existing)
            frontmatter: New frontmatter (None = keep existing, dict = merge)
            append: If True, append content instead of replacing

        Returns:
            Updated note data

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        full_path = self._get_safe_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        # Read existing content
        existing_content = full_path.read_text(encoding='utf-8')
        existing_metadata, existing_body = self.parser.parse_note(existing_content)

        # Determine new content
        if content is not None:
            if append:
                new_body = existing_body + "\n\n" + content
            else:
                new_body = content
        else:
            new_body = existing_body

        # Merge frontmatter
        if frontmatter is not None:
            new_metadata = {**existing_metadata, **frontmatter}
        else:
            new_metadata = existing_metadata

        # Add modified timestamp
        new_metadata['modified'] = datetime.now().isoformat()

        # Format and write
        full_content = self.parser.format_content_with_frontmatter(new_body, new_metadata)
        full_path.write_text(full_content, encoding='utf-8')

        logger.info(f"Updated note: {path}")

        # Invalidate caches
        self.cache.delete(f"note:{path}")
        self.cache.invalidate_pattern("list:")
        self.cache.invalidate_pattern("search:")

        return self.read_note(path)

    def move_note(self, old_path: str, new_path: str) -> Dict[str, Any]:
        """
        Move/rename a note to a new location

        Args:
            old_path: Current relative path to note
            new_path: New relative path (can include subdirectories)

        Returns:
            Moved note data at new location

        Raises:
            FileNotFoundError: If source note doesn't exist
            FileExistsError: If destination already exists
        """
        old_full_path = self._get_safe_path(old_path)

        if not old_full_path.exists():
            raise FileNotFoundError(f"Note not found: {old_path}")

        # Ensure .md extension on new path
        if not new_path.endswith('.md'):
            new_path = f"{new_path}.md"

        # Normalize new path (will apply lowercase if configured)
        new_path_normalized = self._normalize_path_case(new_path)

        new_full_path = self._get_safe_path(new_path)

        if new_full_path.exists():
            raise FileExistsError(f"Note already exists at destination: {new_path_normalized}")

        # Create parent directories for new location
        new_full_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file (preserves metadata)
        old_full_path.rename(new_full_path)

        logger.info(f"Moved note: {old_path} → {new_path_normalized}")

        # Invalidate caches
        self.cache.delete(f"note:{old_path}")
        self.cache.delete(f"note:{new_path_normalized}")
        self.cache.invalidate_pattern("list:")
        self.parser.invalidate_title_map()

        return self.read_note(new_path_normalized)

    def delete_note(self, path: str) -> bool:
        """
        Delete note

        Args:
            path: Relative path to note

        Returns:
            True if deleted

        Raises:
            FileNotFoundError: If note doesn't exist
        """
        full_path = self._get_safe_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        full_path.unlink()

        logger.info(f"Deleted note: {path}")

        # Invalidate caches
        self.cache.delete(f"note:{path}")
        self.cache.invalidate_pattern("list:")
        self.parser.invalidate_title_map()

        return True

    def search_notes(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search notes by content and tags

        Args:
            query: Search query (searches in content)
            tags: Filter by tags
            limit: Maximum results

        Returns:
            List of matching notes with context
        """
        cache_key = f"search:{query}:{','.join(tags or [])}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        results = []
        query_lower = query.lower()

        for md_file in self.vault_path.rglob("*.md"):
            try:
                rel_path = str(md_file.relative_to(self.vault_path))
                content = md_file.read_text(encoding='utf-8')
                metadata, body = self.parser.parse_note(content)

                # Tag filtering
                if tags:
                    note_tags = self.parser.extract_tags(metadata, body)
                    if not any(tag in note_tags for tag in tags):
                        continue

                # Search in content
                if query:
                    search_text = f"{metadata.get('title', '')} {body}".lower()
                    if query_lower not in search_text:
                        continue

                # Extract matching lines
                matches = []
                for line in body.split('\n'):
                    if query_lower in line.lower():
                        matches.append(line.strip())
                        if len(matches) >= 3:  # Limit to 3 matches per file
                            break

                results.append({
                    "path": rel_path,
                    "name": md_file.stem,
                    "title": metadata.get('title', md_file.stem),
                    "tags": self.parser.extract_tags(metadata, body),
                    "matches": matches
                })

                if len(results) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Error searching file during search_notes", exc_info=True)
                continue

        self.cache.set(cache_key, results, ttl=60)  # Shorter TTL for search
        return results

    def get_vault_stats(self) -> Dict[str, Any]:
        """
        Get vault statistics

        Returns:
            Dict with vault stats
        """
        total_notes = len(list(self.vault_path.rglob("*.md")))
        total_size = sum(f.stat().st_size for f in self.vault_path.rglob("*.md"))

        return {
            "vault_path": str(self.vault_path),
            "total_notes": total_notes,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "cache_stats": self.cache.get_stats()
        }

    def invalidate_cache(self, path: Optional[str] = None):
        """
        Invalidate cache (called by file watcher)

        Args:
            path: Specific path to invalidate (None = all)
        """
        if path:
            self.cache.delete(f"note:{path}")
        else:
            self.cache.clear()
        self.cache.invalidate_pattern("list:")
        self.cache.invalidate_pattern("search:")
        self.parser.invalidate_title_map()
        logger.debug(f"Cache invalidated for: {path or 'all'}")
