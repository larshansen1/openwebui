"""
Unit tests for MarkdownParser (app/vault/parser.py)
"""
import pytest
from pathlib import Path
from app.vault.parser import MarkdownParser


@pytest.mark.unit
@pytest.mark.parser
class TestMarkdownParser:
    """Test MarkdownParser functionality"""

    def test_parser_initialization(self, temp_vault_path):
        """Test parser initializes correctly"""
        parser = MarkdownParser(temp_vault_path)
        assert parser.vault_path == temp_vault_path
        assert parser._title_map is None
        assert parser._backlinks_index is None

    def test_parse_note_with_frontmatter(self, parser):
        """Test parsing note with valid frontmatter"""
        content = """---
title: Test Note
tags: [test, example]
---

# Test Content
"""
        metadata, body = parser.parse_note(content)

        assert metadata["title"] == "Test Note"
        assert metadata["tags"] == ["test", "example"]
        assert "# Test Content" in body

    def test_parse_note_without_frontmatter(self, parser):
        """Test parsing note without frontmatter"""
        content = "# Just Content\n\nNo frontmatter here."
        metadata, body = parser.parse_note(content)

        assert metadata == {}
        assert body == content

    def test_parse_note_with_invalid_frontmatter(self, parser):
        """Test parsing note with malformed frontmatter"""
        content = """---
title: Test Note
invalid yaml: [missing closing bracket
---

# Content
"""
        metadata, body = parser.parse_note(content)
        # Should handle gracefully
        assert isinstance(metadata, dict)
        assert isinstance(body, str)

    def test_extract_wiki_links_basic(self, parser):
        """Test extracting basic wiki-links"""
        content = "Link to [[Note A]] and [[Note B]]"
        links = parser.extract_wiki_links(content)

        assert len(links) == 2
        assert "Note A" in links
        assert "Note B" in links

    def test_extract_wiki_links_with_aliases(self, parser):
        """Test extracting wiki-links with aliases"""
        content = "Link to [[Note A|Alias A]] and [[Note B|Alias B]]"
        links = parser.extract_wiki_links(content)

        assert len(links) == 2
        assert "Note A" in links
        assert "Note B" in links
        assert "Alias A" not in links

    def test_extract_wiki_links_with_sections(self, parser):
        """Test extracting wiki-links with section references"""
        content = "Link to [[Note A#Section 1]] and [[Note B#Section 2|Alias]]"
        links = parser.extract_wiki_links(content)

        assert len(links) == 2
        assert "Note A" in links
        assert "Note B" in links

    def test_extract_wiki_links_empty(self, parser):
        """Test extracting from content with no links"""
        content = "No links here, just plain text."
        links = parser.extract_wiki_links(content)

        assert len(links) == 0

    def test_build_title_map(self, parser):
        """Test building title map from vault"""
        title_map = parser.build_title_map()

        # Should include all notes
        assert "welcome" in title_map
        assert "projects" in title_map
        assert "ideas" in title_map

        # Should map titles from frontmatter
        assert title_map["welcome"] == "Welcome.md"
        assert title_map["projects"] == "Projects.md"

    def test_build_title_map_caching(self, parser):
        """Test title map is cached"""
        map1 = parser.build_title_map()
        map2 = parser.build_title_map()

        assert map1 is map2  # Same object reference

    def test_invalidate_title_map(self, parser):
        """Test title map cache invalidation"""
        map1 = parser.build_title_map()
        parser.invalidate_title_map()
        map2 = parser.build_title_map()

        assert map1 is not map2  # Different object reference

    def test_normalize_title(self, parser):
        """Test title normalization"""
        assert parser._normalize_title("My-Note") == "my note"
        assert parser._normalize_title("My_Note") == "my note"
        assert parser._normalize_title("My  Note") == "my note"
        assert parser._normalize_title("MY-NOTE") == "my note"

    def test_resolve_wiki_link_exact(self, parser):
        """Test exact wiki-link resolution"""
        path = parser.resolve_wiki_link("Welcome")
        assert path == "Welcome.md"

        path = parser.resolve_wiki_link("Projects")
        assert path == "Projects.md"

    def test_resolve_wiki_link_case_insensitive(self, parser):
        """Test case-insensitive wiki-link resolution"""
        path = parser.resolve_wiki_link("welcome")
        assert path == "Welcome.md"

        path = parser.resolve_wiki_link("PROJECTS")
        assert path == "Projects.md"

    def test_resolve_wiki_link_with_extension(self, parser):
        """Test wiki-link resolution with .md extension"""
        path = parser.resolve_wiki_link("Welcome.md")
        assert path == "Welcome.md"

    def test_resolve_wiki_link_normalized(self, parser):
        """Test normalized wiki-link resolution (separator variations)"""
        # Create a note with hyphens in filename
        note_path = parser.vault_path / "Test-Note.md"
        note_path.write_text("# Test Note", encoding='utf-8')
        parser.invalidate_title_map()

        # Should match with spaces
        path = parser.resolve_wiki_link("Test Note")
        assert path == "Test-Note.md"

    def test_resolve_wiki_link_fuzzy(self, parser):
        """Test fuzzy wiki-link resolution"""
        # Should match similar titles
        result = parser.resolve_wiki_link_with_score("Welcom")
        assert result is not None
        assert result["path"] == "Welcome.md"
        assert result["score"] >= 0.6
        assert result["match_type"] in ["fuzzy", "exact", "normalized"]

    def test_resolve_wiki_link_not_found(self, parser):
        """Test wiki-link resolution for non-existent note"""
        # Use a completely different name that won't fuzzy match
        path = parser.resolve_wiki_link("Xyz123NonExistent456")
        assert path is None

    def test_resolve_wiki_link_with_score(self, parser):
        """Test wiki-link resolution with similarity score"""
        result = parser.resolve_wiki_link_with_score("Welcome")

        assert result is not None
        assert result["path"] == "Welcome.md"
        assert result["score"] == 1.0
        assert result["match_type"] == "exact"

    def test_resolve_all_links(self, parser):
        """Test resolving all links in content"""
        content = """
        Link to [[Welcome]] and [[Projects]].
        Also see [[Xyz123NonExistent456]].
        """
        resolved = parser.resolve_all_links(content)

        assert resolved["Welcome"] == "Welcome.md"
        assert resolved["Projects"] == "Projects.md"
        assert resolved["Xyz123NonExistent456"] is None

    def test_build_backlinks_index(self, parser):
        """Test building backlinks index"""
        backlinks = parser.build_backlinks_index()

        # Projects.md should have backlinks from Welcome.md and Getting Started.md
        assert "Projects.md" in backlinks
        sources = [source for source, _ in backlinks["Projects.md"]]
        assert "Welcome.md" in sources
        assert "Getting Started.md" in sources

    def test_build_backlinks_index_caching(self, parser):
        """Test backlinks index is cached"""
        index1 = parser.build_backlinks_index()
        index2 = parser.build_backlinks_index()

        assert index1 is index2  # Same object reference

    def test_invalidate_backlinks(self, parser):
        """Test backlinks cache invalidation"""
        index1 = parser.build_backlinks_index()
        parser.invalidate_backlinks()
        index2 = parser.build_backlinks_index()

        assert index1 is not index2  # Different object reference

    def test_extract_link_context(self, parser):
        """Test extracting context around a wiki-link"""
        content = "This is some text before [[Test Note]] and some text after."
        context = parser._extract_link_context(content, "Test Note", max_length=50)

        assert "[[Test Note]]" in context
        assert "before" in context or "after" in context

    def test_extract_link_context_with_alias(self, parser):
        """Test extracting context for link with alias"""
        content = "Link to [[Test Note|Alias]] in the middle."
        context = parser._extract_link_context(content, "Test Note", max_length=50)

        assert "[[Test Note" in context

    def test_extract_link_context_truncation(self, parser):
        """Test context extraction with truncation"""
        content = "A" * 200 + " [[Test Note]] " + "B" * 200
        context = parser._extract_link_context(content, "Test Note", max_length=100)

        assert "..." in context
        assert len(context) <= 150  # Some buffer for ellipsis

    def test_get_backlinks(self, parser):
        """Test getting backlinks for a specific note"""
        backlinks = parser.get_backlinks("Projects.md")

        assert len(backlinks) >= 2  # At least Welcome and Getting Started
        assert all("source_path" in bl for bl in backlinks)
        assert all("source_name" in bl for bl in backlinks)
        assert all("context" in bl for bl in backlinks)

    def test_get_backlinks_no_backlinks(self, parser):
        """Test getting backlinks for note with no backlinks"""
        backlinks = parser.get_backlinks("Orphan Note.md")

        assert len(backlinks) == 0

    def test_format_content_with_frontmatter(self, parser, sample_frontmatter):
        """Test formatting content with frontmatter"""
        content = "# Test Content\n\nSome body text."
        formatted = parser.format_content_with_frontmatter(content, sample_frontmatter)

        assert "---" in formatted
        assert "title: Test Note" in formatted
        assert "# Test Content" in formatted

    def test_format_content_without_frontmatter(self, parser):
        """Test formatting content without frontmatter"""
        content = "# Test Content"
        formatted = parser.format_content_with_frontmatter(content, {})

        assert formatted == content

    def test_extract_tags_from_frontmatter(self, parser):
        """Test extracting tags from frontmatter"""
        metadata = {"tags": ["tag1", "tag2"]}
        content = "Some content"
        tags = parser.extract_tags(metadata, content)

        assert "tag1" in tags
        assert "tag2" in tags

    def test_extract_tags_from_inline(self, parser):
        """Test extracting inline tags"""
        metadata = {}
        content = "Content with #tag1 and #tag2"
        tags = parser.extract_tags(metadata, content)

        assert "tag1" in tags
        assert "tag2" in tags

    def test_extract_tags_mixed(self, parser):
        """Test extracting tags from both frontmatter and inline"""
        metadata = {"tags": ["frontmatter-tag"]}
        content = "Content with #inline-tag"
        tags = parser.extract_tags(metadata, content)

        assert "frontmatter-tag" in tags
        assert "inline-tag" in tags
        assert len(tags) == 2

    def test_extract_tags_deduplicate(self, parser):
        """Test tag extraction deduplicates"""
        metadata = {"tags": ["duplicate"]}
        content = "Content with #duplicate"
        tags = parser.extract_tags(metadata, content)

        assert tags.count("duplicate") == 1

    def test_extract_tags_string_format(self, parser):
        """Test extracting tags from string format in frontmatter"""
        metadata = {"tags": "tag1, tag2, tag3"}
        content = ""
        tags = parser.extract_tags(metadata, content)

        assert "tag1" in tags
        assert "tag2" in tags
        assert "tag3" in tags

    def test_wiki_link_pattern(self, parser):
        """Test wiki-link regex pattern"""
        test_cases = [
            ("[[Simple]]", ["Simple"]),
            ("[[With Alias|alias]]", ["With Alias|alias"]),
            ("[[With#Section]]", ["With#Section"]),
            ("Multiple [[First]] and [[Second]]", ["First", "Second"]),
            ("No links here", [])
        ]

        for content, expected in test_cases:
            matches = parser.WIKI_LINK_PATTERN.findall(content)
            assert matches == expected

    def test_nested_folder_resolution(self, parser):
        """Test resolving wiki-links to notes in subfolders"""
        path = parser.resolve_wiki_link("Nested Note")
        assert path == "subfolder/Nested Note.md"

    def test_backlinks_from_nested_note(self, parser):
        """Test backlinks work with nested notes"""
        backlinks = parser.build_backlinks_index()

        # Welcome should have a backlink from the nested note
        welcome_backlinks = [source for source, _ in backlinks.get("Welcome.md", [])]
        assert "subfolder/Nested Note.md" in welcome_backlinks
