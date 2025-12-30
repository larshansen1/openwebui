"""
Markdown structure parser for extracting and manipulating document structure.
Provides heading hierarchy, block references, and table of contents generation.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Types of markdown blocks"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    QUOTE = "quote"
    TABLE = "table"
    BLOCK_REF = "block_ref"


@dataclass
class MarkdownHeading:
    """Represents a markdown heading with its content and position"""
    level: int  # 1-6 (H1-H6)
    text: str  # Heading text without # markers
    anchor: str  # Slugified anchor for #section links
    start_line: int  # Line number where heading starts (0-indexed)
    end_line: int  # Line number where heading content ends (0-indexed)
    content: str  # Content between this heading and next same/higher level
    children: List['MarkdownHeading'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "level": self.level,
            "text": self.text,
            "anchor": self.anchor,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "has_children": len(self.children) > 0,
            "child_count": len(self.children)
        }


@dataclass
class MarkdownBlock:
    """Represents a markdown block (paragraph, list, code, etc.)"""
    block_type: BlockType
    content: str
    start_line: int
    end_line: int
    block_id: Optional[str] = None  # For ^block-id references
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "type": self.block_type.value,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "block_id": self.block_id,
            "metadata": self.metadata
        }


@dataclass
class DocumentStructure:
    """Complete document structure with headings, blocks, and metadata"""
    headings: List[MarkdownHeading]
    blocks: List[MarkdownBlock]
    block_refs: Dict[str, MarkdownBlock]  # Map of block_id -> block
    toc: List[Dict[str, Any]]  # Table of contents
    word_count: int
    reading_time_minutes: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "headings": [h.to_dict() for h in self.headings],
            "blocks": [b.to_dict() for b in self.blocks],
            "block_refs": {bid: b.to_dict() for bid, b in self.block_refs.items()},
            "toc": self.toc,
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes
        }


class StructureParser:
    """Parser for markdown document structure"""

    # Regex patterns
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+\^([a-zA-Z0-9-_]+))?\s*$', re.MULTILINE)
    BLOCK_REF_PATTERN = re.compile(r'\^([a-zA-Z0-9-_]+)\s*$')
    CODE_BLOCK_PATTERN = re.compile(r'^```')
    LIST_PATTERN = re.compile(r'^(\s*)([-*+]|\d+\.)\s+')
    QUOTE_PATTERN = re.compile(r'^>\s+')
    TABLE_PATTERN = re.compile(r'^\|.+\|')

    def __init__(self):
        """Initialize structure parser"""
        pass

    def parse_structure(self, content: str) -> DocumentStructure:
        """
        Parse complete document structure

        Args:
            content: Markdown content to parse

        Returns:
            DocumentStructure with all parsed components
        """
        lines = content.split('\n')

        # Parse headings
        headings = self._parse_headings(content, lines)

        # Parse blocks
        blocks = self._parse_blocks(content, lines)

        # Build block references map
        block_refs = {b.block_id: b for b in blocks if b.block_id}

        # Generate TOC
        toc = self._generate_toc(headings)

        # Calculate word count (excluding code blocks)
        word_count = self._calculate_word_count(content)

        # Calculate reading time (250 WPM average)
        reading_time_minutes = round(word_count / 250, 1) if word_count > 0 else 0

        return DocumentStructure(
            headings=headings,
            blocks=blocks,
            block_refs=block_refs,
            toc=toc,
            word_count=word_count,
            reading_time_minutes=reading_time_minutes
        )

    def _parse_headings(self, content: str, lines: List[str]) -> List[MarkdownHeading]:
        """
        Parse all headings with hierarchy

        Args:
            content: Full markdown content
            lines: Content split into lines

        Returns:
            List of MarkdownHeading objects with parent-child relationships
        """
        headings = []
        stack: List[MarkdownHeading] = []  # Stack for building hierarchy

        for i, line in enumerate(lines):
            match = re.match(r'^(#{1,6})\s+(.+?)(?:\s+\^([a-zA-Z0-9-_]+))?\s*$', line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                block_id = match.group(3)

                # Create anchor (slugify)
                anchor = self._slugify(text)

                # Find content for this heading (until next same/higher level heading)
                end_line = self._find_heading_end(lines, i, level)
                heading_content = '\n'.join(lines[i+1:end_line+1])

                heading = MarkdownHeading(
                    level=level,
                    text=text,
                    anchor=anchor,
                    start_line=i,
                    end_line=end_line,
                    content=heading_content,
                    children=[]
                )

                # Build hierarchy
                # Pop stack until we find parent (lower level number = higher hierarchy)
                while stack and stack[-1].level >= level:
                    stack.pop()

                # Add as child to parent if exists
                if stack:
                    stack[-1].children.append(heading)
                else:
                    # Top-level heading
                    headings.append(heading)

                # Push current heading onto stack
                stack.append(heading)

        return headings

    def _find_heading_end(self, lines: List[str], start_line: int, level: int) -> int:
        """
        Find the end line of a heading's content

        Args:
            lines: All lines in document
            start_line: Line where heading starts
            level: Heading level

        Returns:
            End line index (exclusive of next heading)
        """
        for i in range(start_line + 1, len(lines)):
            match = re.match(r'^(#{1,6})\s+', lines[i])
            if match:
                next_level = len(match.group(1))
                if next_level <= level:
                    return i - 1

        # No next heading found, content goes to end of document
        return len(lines) - 1

    def _slugify(self, text: str) -> str:
        """
        Convert heading text to URL-safe anchor

        Args:
            text: Heading text

        Returns:
            Slugified anchor string
        """
        # Convert to lowercase
        slug = text.lower()

        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)

        # Remove special characters (keep alphanumeric and hyphens)
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)

        # Strip leading/trailing hyphens
        slug = slug.strip('-')

        return slug

    def _parse_blocks(self, content: str, lines: List[str]) -> List[MarkdownBlock]:
        """
        Parse all blocks in the document

        Args:
            content: Full markdown content
            lines: Content split into lines

        Returns:
            List of MarkdownBlock objects
        """
        blocks = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Skip headings (handled separately)
            if re.match(r'^#{1,6}\s+', line):
                i += 1
                continue

            # Code block
            if self.CODE_BLOCK_PATTERN.match(line):
                block, end_line = self._parse_code_block(lines, i)
                blocks.append(block)
                i = end_line + 1
                continue

            # List
            if self.LIST_PATTERN.match(line):
                block, end_line = self._parse_list_block(lines, i)
                blocks.append(block)
                i = end_line + 1
                continue

            # Quote
            if self.QUOTE_PATTERN.match(line):
                block, end_line = self._parse_quote_block(lines, i)
                blocks.append(block)
                i = end_line + 1
                continue

            # Table
            if self.TABLE_PATTERN.match(line):
                block, end_line = self._parse_table_block(lines, i)
                blocks.append(block)
                i = end_line + 1
                continue

            # Default: paragraph
            block, end_line = self._parse_paragraph_block(lines, i)
            blocks.append(block)
            i = end_line + 1

        return blocks

    def _parse_code_block(self, lines: List[str], start: int) -> Tuple[MarkdownBlock, int]:
        """Parse code block"""
        end = start + 1
        while end < len(lines) and not self.CODE_BLOCK_PATTERN.match(lines[end]):
            end += 1

        content = '\n'.join(lines[start:end+1])
        block_id = self._extract_block_id(lines[end] if end < len(lines) else '')

        return MarkdownBlock(
            block_type=BlockType.CODE_BLOCK,
            content=content,
            start_line=start,
            end_line=end,
            block_id=block_id
        ), end

    def _parse_list_block(self, lines: List[str], start: int) -> Tuple[MarkdownBlock, int]:
        """Parse list block"""
        end = start
        while end + 1 < len(lines):
            next_line = lines[end + 1]
            # Continue if next line is list item or indented continuation
            if self.LIST_PATTERN.match(next_line) or (next_line.strip() and next_line.startswith('  ')):
                end += 1
            else:
                break

        content = '\n'.join(lines[start:end+1])
        block_id = self._extract_block_id(lines[end])

        return MarkdownBlock(
            block_type=BlockType.LIST,
            content=content,
            start_line=start,
            end_line=end,
            block_id=block_id
        ), end

    def _parse_quote_block(self, lines: List[str], start: int) -> Tuple[MarkdownBlock, int]:
        """Parse quote block"""
        end = start
        while end + 1 < len(lines) and self.QUOTE_PATTERN.match(lines[end + 1]):
            end += 1

        content = '\n'.join(lines[start:end+1])
        block_id = self._extract_block_id(lines[end])

        return MarkdownBlock(
            block_type=BlockType.QUOTE,
            content=content,
            start_line=start,
            end_line=end,
            block_id=block_id
        ), end

    def _parse_table_block(self, lines: List[str], start: int) -> Tuple[MarkdownBlock, int]:
        """Parse table block"""
        end = start
        while end + 1 < len(lines) and self.TABLE_PATTERN.match(lines[end + 1]):
            end += 1

        content = '\n'.join(lines[start:end+1])
        block_id = self._extract_block_id(lines[end])

        return MarkdownBlock(
            block_type=BlockType.TABLE,
            content=content,
            start_line=start,
            end_line=end,
            block_id=block_id
        ), end

    def _parse_paragraph_block(self, lines: List[str], start: int) -> Tuple[MarkdownBlock, int]:
        """Parse paragraph block"""
        end = start
        while end + 1 < len(lines):
            next_line = lines[end + 1]
            # Continue if next line is not empty and not a special block
            if (next_line.strip() and
                not re.match(r'^#{1,6}\s+', next_line) and
                not self.CODE_BLOCK_PATTERN.match(next_line) and
                not self.LIST_PATTERN.match(next_line) and
                not self.QUOTE_PATTERN.match(next_line) and
                not self.TABLE_PATTERN.match(next_line)):
                end += 1
            else:
                break

        content = '\n'.join(lines[start:end+1])
        block_id = self._extract_block_id(lines[end])

        return MarkdownBlock(
            block_type=BlockType.PARAGRAPH,
            content=content,
            start_line=start,
            end_line=end,
            block_id=block_id
        ), end

    def _extract_block_id(self, line: str) -> Optional[str]:
        """
        Extract block ID from line ending with ^block-id

        Args:
            line: Line to check for block reference

        Returns:
            Block ID if found, None otherwise
        """
        match = self.BLOCK_REF_PATTERN.search(line)
        return match.group(1) if match else None

    def _generate_toc(self, headings: List[MarkdownHeading], max_depth: int = 6) -> List[Dict[str, Any]]:
        """
        Generate hierarchical table of contents

        Args:
            headings: List of top-level headings with children
            max_depth: Maximum depth to include

        Returns:
            List of TOC entries
        """
        toc = []

        def add_to_toc(heading: MarkdownHeading, depth: int = 1):
            if depth > max_depth:
                return

            toc.append({
                "level": heading.level,
                "text": heading.text,
                "anchor": heading.anchor,
                "line": heading.start_line
            })

            # Add children
            for child in heading.children:
                add_to_toc(child, depth + 1)

        for heading in headings:
            add_to_toc(heading)

        return toc

    def _calculate_word_count(self, content: str) -> int:
        """
        Calculate word count excluding code blocks

        Args:
            content: Markdown content

        Returns:
            Word count
        """
        # Remove code blocks
        content_no_code = re.sub(r'```[\s\S]*?```', '', content)

        # Remove inline code
        content_no_code = re.sub(r'`[^`]+`', '', content_no_code)

        # Count words
        words = re.findall(r'\b\w+\b', content_no_code)
        return len(words)

    def _normalize_heading(self, text: str) -> str:
        """
        Normalize heading text for fuzzy matching
        - Remove markdown formatting (**, *, ~~, etc.)
        - Remove trailing punctuation (., :, ?, !)
        - Strip whitespace
        - Lowercase
        """
        # Remove markdown bold, italic, strikethrough
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
        text = re.sub(r'~~([^~]+)~~', r'\1', text)      # ~~strikethrough~~

        # Remove trailing punctuation
        text = re.sub(r'[.:;,!?]+$', '', text)

        # Strip and lowercase
        return text.strip().lower()

    def extract_section(self, content: str, section_ref: str) -> Optional[str]:
        """
        Extract section content by heading reference (with fuzzy matching)

        Args:
            content: Full markdown content
            section_ref: Section reference (heading text or anchor)
                        Supports fuzzy matching - ignores markdown formatting,
                        punctuation, and case differences

        Returns:
            Section content if found, None otherwise
        """
        lines = content.split('\n')
        headings = self._parse_headings(content, lines)

        # Normalize the search term
        normalized_ref = self._normalize_heading(section_ref)

        # Search all headings (including nested)
        def find_heading(headings_list: List[MarkdownHeading]) -> Optional[MarkdownHeading]:
            for h in headings_list:
                # Match by text (fuzzy) or anchor (exact, case-insensitive)
                normalized_heading = self._normalize_heading(h.text)
                if (normalized_heading == normalized_ref or
                    h.anchor.lower() == section_ref.lower()):
                    return h
                # Search children
                result = find_heading(h.children)
                if result:
                    return result
            return None

        heading = find_heading(headings)
        if heading:
            # Return heading line + content
            section_lines = lines[heading.start_line:heading.end_line+1]
            return '\n'.join(section_lines)

        return None

    def extract_block(self, content: str, block_id: str) -> Optional[str]:
        """
        Extract block content by block ID

        Args:
            content: Full markdown content
            block_id: Block ID (without ^ prefix)

        Returns:
            Block content if found, None otherwise
        """
        structure = self.parse_structure(content)

        if block_id in structure.block_refs:
            return structure.block_refs[block_id].content

        return None

    def update_section(self, content: str, section_ref: str, new_content: str) -> str:
        """
        Update section content by heading reference

        Args:
            content: Full markdown content
            section_ref: Section reference (heading text or anchor)
            new_content: New content for the section (without heading line)

        Returns:
            Updated markdown content

        Raises:
            ValueError: If section not found
        """
        lines = content.split('\n')
        headings = self._parse_headings(content, lines)

        # Find heading
        def find_heading(headings_list: List[MarkdownHeading]) -> Optional[MarkdownHeading]:
            for h in headings_list:
                if (h.text.lower() == section_ref.lower() or
                    h.anchor.lower() == section_ref.lower()):
                    return h
                result = find_heading(h.children)
                if result:
                    return result
            return None

        heading = find_heading(headings)
        if not heading:
            raise ValueError(f"Section not found: {section_ref}")

        # Replace content (keep heading line, replace body)
        new_lines = (
            lines[:heading.start_line+1] +  # Before + heading line
            new_content.split('\n') +  # New content
            lines[heading.end_line+1:]  # After section
        )

        return '\n'.join(new_lines)

    def update_block(self, content: str, block_id: str, new_content: str) -> str:
        """
        Update block content by block ID

        Args:
            content: Full markdown content
            block_id: Block ID (without ^ prefix)
            new_content: New content for the block

        Returns:
            Updated markdown content

        Raises:
            ValueError: If block not found
        """
        structure = self.parse_structure(content)

        if block_id not in structure.block_refs:
            raise ValueError(f"Block not found: ^{block_id}")

        block = structure.block_refs[block_id]
        lines = content.split('\n')

        # Preserve block ID marker if it exists
        block_id_marker = f" ^{block_id}"
        if new_content.endswith(block_id_marker):
            # Already has marker
            pass
        elif not self.BLOCK_REF_PATTERN.search(new_content):
            # Add marker to last line
            new_content_lines = new_content.split('\n')
            new_content_lines[-1] = new_content_lines[-1] + block_id_marker
            new_content = '\n'.join(new_content_lines)

        # Replace block
        new_lines = (
            lines[:block.start_line] +
            new_content.split('\n') +
            lines[block.end_line+1:]
        )

        return '\n'.join(new_lines)
