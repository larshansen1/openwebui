"""
Markdown parser for Obsidian notes
Handles frontmatter extraction and wiki-link resolution
"""
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from difflib import SequenceMatcher
import frontmatter

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parser for Obsidian markdown files"""

    # Regex pattern for wiki-links: [[note name]] or [[note name|alias]]
    WIKI_LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

    def __init__(self, vault_path: Path):
        """
        Initialize parser

        Args:
            vault_path: Path to vault root
        """
        self.vault_path = vault_path
        # Cache for note title to path mapping
        self._title_map: Optional[Dict[str, str]] = None

    def parse_note(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Parse note content into frontmatter and body

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (frontmatter dict, body content)
        """
        try:
            post = frontmatter.loads(content)
            return dict(post.metadata), post.content
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
            return {}, content

    def extract_wiki_links(self, content: str) -> List[str]:
        """
        Extract all wiki-links from content

        Args:
            content: Markdown content

        Returns:
            List of wiki-link targets (without [[ ]])
        """
        matches = self.WIKI_LINK_PATTERN.findall(content)
        # Extract link target (before | if alias present)
        links = []
        for match in matches:
            # Handle [[note name|alias]] format
            if '|' in match:
                link = match.split('|')[0].strip()
            else:
                link = match.strip()
            # Remove section references (#section)
            if '#' in link:
                link = link.split('#')[0].strip()
            if link:
                links.append(link)
        return links

    def build_title_map(self) -> Dict[str, str]:
        """
        Build mapping of note titles/names to file paths

        Returns:
            Dict mapping titles to relative paths
        """
        if self._title_map is not None:
            return self._title_map

        title_map = {}

        # Walk through all markdown files
        for md_file in self.vault_path.rglob("*.md"):
            rel_path = str(md_file.relative_to(self.vault_path))

            # Add mapping by filename (without .md)
            filename = md_file.stem
            title_map[filename.lower()] = rel_path

            # Try to get title from frontmatter
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                metadata, _ = self.parse_note(content)

                if 'title' in metadata:
                    title = metadata['title']
                    if isinstance(title, str):
                        title_map[title.lower()] = rel_path
            except Exception as e:
                logger.debug(f"Could not read frontmatter from {rel_path}: {e}")
                continue

        self._title_map = title_map
        return title_map

    def _normalize_title(self, title: str) -> str:
        """
        Normalize title for fuzzy matching
        Converts hyphens/underscores to spaces, lowercase, strips
        """
        # Replace hyphens and underscores with spaces
        normalized = title.replace('-', ' ').replace('_', ' ')
        # Remove multiple spaces
        normalized = ' '.join(normalized.split())
        # Lowercase
        return normalized.lower()

    def resolve_wiki_link(self, link: str) -> Optional[str]:
        """
        Resolve wiki-link to actual file path with fuzzy matching

        Handles common variations:
        - Case differences: "My Note" vs "my note"
        - Separators: "my-note" vs "my note" vs "my_note"
        - Extensions: "my note" vs "my note.md"

        Args:
            link: Wiki-link target (e.g., "My Note")

        Returns:
            Relative path to file, or None if not found
        """
        result = self.resolve_wiki_link_with_score(link)
        return result["path"] if result else None

    def resolve_wiki_link_with_score(self, link: str) -> Optional[Dict[str, Any]]:
        """
        Resolve wiki-link to actual file path with similarity score

        Handles common variations and returns the best match with a confidence score.

        Args:
            link: Wiki-link target (e.g., "My Note")

        Returns:
            Dict with 'path', 'title', 'score' (0.0-1.0), 'match_type' or None if not found
        """
        title_map = self.build_title_map()

        # Try exact match (case-insensitive)
        link_lower = link.lower()
        if link_lower in title_map:
            return {
                "path": title_map[link_lower],
                "title": link_lower,
                "score": 1.0,
                "match_type": "exact"
            }

        # Try with .md extension
        if not link.endswith('.md'):
            link_md = f"{link}.md"
            if link_md.lower() in title_map:
                return {
                    "path": title_map[link_md.lower()],
                    "title": link_md.lower(),
                    "score": 1.0,
                    "match_type": "exact"
                }

        # Try fuzzy matching (normalize separators)
        normalized_link = self._normalize_title(link)

        for title, path in title_map.items():
            if self._normalize_title(title) == normalized_link:
                logger.debug(f"Fuzzy matched: {link} → {path}")
                return {
                    "path": path,
                    "title": title,
                    "score": 0.95,
                    "match_type": "normalized"
                }

        # Find best fuzzy match using similarity scoring
        best_match = None
        best_score = 0.0

        for title, path in title_map.items():
            # Calculate similarity between normalized strings
            score = SequenceMatcher(None, normalized_link, self._normalize_title(title)).ratio()

            if score > best_score and score >= 0.6:  # Minimum threshold
                best_score = score
                best_match = {
                    "path": path,
                    "title": title,
                    "score": score,
                    "match_type": "fuzzy"
                }

        if best_match:
            logger.debug(f"Fuzzy matched with score {best_score:.2f}: {link} → {best_match['path']}")
            return best_match

        return None

    def resolve_all_links(self, content: str) -> Dict[str, Optional[str]]:
        """
        Resolve all wiki-links in content

        Args:
            content: Markdown content

        Returns:
            Dict mapping link text to resolved path (or None if not found)
        """
        links = self.extract_wiki_links(content)
        resolved = {}

        for link in links:
            if link not in resolved:  # Avoid duplicate resolution
                resolved[link] = self.resolve_wiki_link(link)

        return resolved

    def invalidate_title_map(self):
        """Invalidate title map cache (call when files change)"""
        self._title_map = None

    def format_content_with_frontmatter(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Format content with frontmatter

        Args:
            content: Markdown body
            metadata: Frontmatter metadata

        Returns:
            Complete markdown with frontmatter
        """
        if not metadata:
            return content

        post = frontmatter.Post(content, **metadata)
        return frontmatter.dumps(post)

    def extract_tags(self, metadata: Dict[str, Any], content: str) -> List[str]:
        """
        Extract tags from frontmatter and inline tags

        Args:
            metadata: Frontmatter metadata
            content: Markdown content

        Returns:
            List of unique tags
        """
        tags = set()

        # From frontmatter
        if 'tags' in metadata:
            fm_tags = metadata['tags']
            if isinstance(fm_tags, list):
                tags.update(str(t).strip() for t in fm_tags if t)
            elif isinstance(fm_tags, str):
                # Handle comma-separated or space-separated
                tags.update(t.strip() for t in re.split(r'[,\s]+', fm_tags) if t.strip())

        # From inline tags (#tag)
        inline_tags = re.findall(r'#([\w-]+)', content)
        tags.update(inline_tags)

        return sorted(list(tags))
