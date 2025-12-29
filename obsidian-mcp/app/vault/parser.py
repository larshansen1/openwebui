"""
Markdown parser for Obsidian notes
Handles frontmatter extraction and wiki-link resolution
"""
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
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

    def resolve_wiki_link(self, link: str) -> Optional[str]:
        """
        Resolve wiki-link to actual file path

        Args:
            link: Wiki-link target (e.g., "My Note")

        Returns:
            Relative path to file, or None if not found
        """
        title_map = self.build_title_map()

        # Try exact match (case-insensitive)
        link_lower = link.lower()
        if link_lower in title_map:
            return title_map[link_lower]

        # Try with .md extension
        if not link.endswith('.md'):
            link_md = f"{link}.md"
            if link_md.lower() in title_map:
                return title_map[link_md.lower()]

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
