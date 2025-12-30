"""
Unit tests for structure parsing (headings, blocks, TOC, sections)
"""
import pytest
from app.vault.structure import (
    StructureParser,
    MarkdownHeading,
    MarkdownBlock,
    DocumentStructure,
    BlockType
)


class TestHeadingParsing:
    """Tests for heading parsing and hierarchy"""

    def test_parse_single_heading(self):
        """Test parsing a single heading"""
        parser = StructureParser()
        content = "# Main Title\n\nSome content here."

        structure = parser.parse_structure(content)

        assert len(structure.headings) == 1
        assert structure.headings[0].level == 1
        assert structure.headings[0].text == "Main Title"
        assert structure.headings[0].anchor == "main-title"
        assert structure.headings[0].start_line == 0

    def test_parse_multiple_headings_same_level(self):
        """Test parsing multiple headings at the same level"""
        parser = StructureParser()
        content = """# First
Content 1

# Second
Content 2

# Third
Content 3"""

        structure = parser.parse_structure(content)

        assert len(structure.headings) == 3
        assert structure.headings[0].text == "First"
        assert structure.headings[1].text == "Second"
        assert structure.headings[2].text == "Third"
        assert all(h.level == 1 for h in structure.headings)

    def test_parse_nested_headings(self):
        """Test parsing nested heading hierarchy"""
        parser = StructureParser()
        content = """# Main Title

## Subsection 1
Content here

## Subsection 2
More content

### Deep section
Even more content"""

        structure = parser.parse_structure(content)

        # Should have 1 top-level heading
        assert len(structure.headings) == 1
        assert structure.headings[0].text == "Main Title"

        # Should have 2 children
        assert len(structure.headings[0].children) == 2
        assert structure.headings[0].children[0].text == "Subsection 1"
        assert structure.headings[0].children[1].text == "Subsection 2"

        # Second child should have 1 child
        assert len(structure.headings[0].children[1].children) == 1
        assert structure.headings[0].children[1].children[0].text == "Deep section"

    def test_parse_all_heading_levels(self):
        """Test parsing all heading levels H1-H6"""
        parser = StructureParser()
        content = """# Level 1
## Level 2
### Level 3
#### Level 4
##### Level 5
###### Level 6"""

        structure = parser.parse_structure(content)

        # Verify hierarchy
        h1 = structure.headings[0]
        assert h1.level == 1
        assert h1.text == "Level 1"

        h2 = h1.children[0]
        assert h2.level == 2
        assert h2.text == "Level 2"

        h3 = h2.children[0]
        assert h3.level == 3
        assert h3.text == "Level 3"

    def test_heading_with_special_characters(self):
        """Test heading with special characters in text"""
        parser = StructureParser()
        content = "# Hello, World! & Stuff (2024)"

        structure = parser.parse_structure(content)

        assert structure.headings[0].text == "Hello, World! & Stuff (2024)"
        # Anchor should be slugified
        assert structure.headings[0].anchor == "hello-world-stuff-2024"

    def test_heading_with_numbers(self):
        """Test heading with numbers"""
        parser = StructureParser()
        content = "## Step 123: Do Something"

        structure = parser.parse_structure(content)

        assert structure.headings[0].text == "Step 123: Do Something"
        assert structure.headings[0].anchor == "step-123-do-something"

    def test_heading_anchor_slugification(self):
        """Test anchor slugification edge cases"""
        parser = StructureParser()
        test_cases = [
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special!@#$%Chars", "specialchars"),
            ("CamelCase Text", "camelcase-text"),
            ("trailing-hyphens--", "trailing-hyphens"),
            ("--leading-hyphens", "leading-hyphens"),
        ]

        for text, expected_anchor in test_cases:
            content = f"# {text}"
            structure = parser.parse_structure(content)
            assert structure.headings[0].anchor == expected_anchor

    def test_heading_content_extraction(self):
        """Test that heading content is correctly extracted"""
        parser = StructureParser()
        content = """# Main

This is the content
under the main heading.

## Subsection

This is subsection content."""

        structure = parser.parse_structure(content)

        main_heading = structure.headings[0]
        assert "This is the content" in main_heading.content
        assert "This is subsection content" in main_heading.content

    def test_heading_with_block_id(self):
        """Test heading with block ID reference"""
        parser = StructureParser()
        content = "# Main Title ^heading-1"

        structure = parser.parse_structure(content)

        assert structure.headings[0].text == "Main Title"
        # Block ID should be stripped from heading text
        assert "^heading-1" not in structure.headings[0].text

    def test_complex_nested_hierarchy(self):
        """Test complex nested hierarchy with multiple branches"""
        parser = StructureParser()
        content = """# Root

## Branch 1

### Leaf 1.1
### Leaf 1.2

## Branch 2

### Leaf 2.1

#### Deep 2.1.1

## Branch 3"""

        structure = parser.parse_structure(content)

        root = structure.headings[0]
        assert len(root.children) == 3

        # Branch 1 has 2 leaves
        assert len(root.children[0].children) == 2

        # Branch 2 has 1 leaf with 1 deep child
        assert len(root.children[1].children) == 1
        assert len(root.children[1].children[0].children) == 1


class TestBlockParsing:
    """Tests for block parsing"""

    def test_parse_paragraph_block(self):
        """Test parsing a simple paragraph"""
        parser = StructureParser()
        content = "This is a paragraph.\nIt has multiple lines."

        structure = parser.parse_structure(content)

        paragraphs = [b for b in structure.blocks if b.block_type == BlockType.PARAGRAPH]
        assert len(paragraphs) == 1
        assert "This is a paragraph" in paragraphs[0].content

    def test_parse_code_block(self):
        """Test parsing a code block"""
        parser = StructureParser()
        content = """```python
def hello():
    print("world")
```"""

        structure = parser.parse_structure(content)

        code_blocks = [b for b in structure.blocks if b.block_type == BlockType.CODE_BLOCK]
        assert len(code_blocks) == 1
        assert "def hello()" in code_blocks[0].content

    def test_parse_list_block(self):
        """Test parsing a list"""
        parser = StructureParser()
        content = """- Item 1
- Item 2
- Item 3"""

        structure = parser.parse_structure(content)

        lists = [b for b in structure.blocks if b.block_type == BlockType.LIST]
        assert len(lists) == 1
        assert "Item 1" in lists[0].content
        assert "Item 3" in lists[0].content

    def test_parse_numbered_list(self):
        """Test parsing a numbered list"""
        parser = StructureParser()
        content = """1. First
2. Second
3. Third"""

        structure = parser.parse_structure(content)

        lists = [b for b in structure.blocks if b.block_type == BlockType.LIST]
        assert len(lists) == 1
        assert "First" in lists[0].content

    def test_parse_quote_block(self):
        """Test parsing a blockquote"""
        parser = StructureParser()
        content = """> This is a quote
> with multiple lines"""

        structure = parser.parse_structure(content)

        quotes = [b for b in structure.blocks if b.block_type == BlockType.QUOTE]
        assert len(quotes) == 1
        assert "This is a quote" in quotes[0].content

    def test_parse_table_block(self):
        """Test parsing a markdown table"""
        parser = StructureParser()
        content = """| Col1 | Col2 |
|------|------|
| A    | B    |"""

        structure = parser.parse_structure(content)

        tables = [b for b in structure.blocks if b.block_type == BlockType.TABLE]
        assert len(tables) == 1
        assert "Col1" in tables[0].content

    def test_block_with_reference_id(self):
        """Test block with ^block-id reference"""
        parser = StructureParser()
        content = "This is a paragraph with a reference. ^para-1"

        structure = parser.parse_structure(content)

        assert len(structure.block_refs) == 1
        assert "para-1" in structure.block_refs
        assert structure.block_refs["para-1"].content == content

    def test_multiple_blocks_with_ids(self):
        """Test multiple blocks with different IDs"""
        parser = StructureParser()
        content = """Paragraph 1 ^p1

Paragraph 2 ^p2

Paragraph 3 ^p3"""

        structure = parser.parse_structure(content)

        assert len(structure.block_refs) == 3
        assert "p1" in structure.block_refs
        assert "p2" in structure.block_refs
        assert "p3" in structure.block_refs

    def test_indented_list_continuation(self):
        """Test list with indented continuation"""
        parser = StructureParser()
        content = """- Item 1
  with continuation
- Item 2"""

        structure = parser.parse_structure(content)

        lists = [b for b in structure.blocks if b.block_type == BlockType.LIST]
        assert len(lists) == 1
        assert "with continuation" in lists[0].content


class TestTOCGeneration:
    """Tests for table of contents generation"""

    def test_generate_basic_toc(self):
        """Test basic TOC generation"""
        parser = StructureParser()
        content = """# Main
## Section 1
## Section 2
### Subsection 2.1"""

        structure = parser.parse_structure(content)

        assert len(structure.toc) == 4
        assert structure.toc[0]['text'] == "Main"
        assert structure.toc[0]['level'] == 1
        assert structure.toc[1]['text'] == "Section 1"
        assert structure.toc[1]['level'] == 2

    def test_toc_with_max_depth(self):
        """Test TOC respecting max_depth"""
        parser = StructureParser()
        content = """# H1
## H2
### H3
#### H4"""

        structure = parser.parse_structure(content)

        # All headings should be in TOC
        assert len(structure.toc) == 4

        # Filter by max_depth=2
        toc_filtered = [e for e in structure.toc if e['level'] <= 2]
        assert len(toc_filtered) == 2

    def test_toc_includes_anchors(self):
        """Test that TOC includes anchor links"""
        parser = StructureParser()
        content = """# Main Title
## Sub Section"""

        structure = parser.parse_structure(content)

        assert structure.toc[0]['anchor'] == "main-title"
        assert structure.toc[1]['anchor'] == "sub-section"

    def test_toc_includes_line_numbers(self):
        """Test that TOC includes line numbers"""
        parser = StructureParser()
        content = """# First

Content here

## Second"""

        structure = parser.parse_structure(content)

        assert structure.toc[0]['line'] == 0
        assert structure.toc[1]['line'] == 4

    def test_empty_toc(self):
        """Test TOC with no headings"""
        parser = StructureParser()
        content = "Just some text without any headings."

        structure = parser.parse_structure(content)

        assert len(structure.toc) == 0


class TestSectionExtraction:
    """Tests for section extraction"""

    def test_extract_section_by_text(self):
        """Test extracting section by heading text"""
        parser = StructureParser()
        content = """# Main

## Target Section

This is the content
we want to extract.

## Other Section"""

        section = parser.extract_section(content, "Target Section")

        assert section is not None
        assert "## Target Section" in section
        assert "This is the content" in section
        assert "Other Section" not in section

    def test_extract_section_by_anchor(self):
        """Test extracting section by anchor"""
        parser = StructureParser()
        content = """# Main Title

## Sub Section

Content here."""

        section = parser.extract_section(content, "sub-section")

        assert section is not None
        assert "## Sub Section" in section

    def test_extract_section_case_insensitive(self):
        """Test section extraction is case-insensitive"""
        parser = StructureParser()
        content = """# MAIN TITLE

Content here."""

        section1 = parser.extract_section(content, "Main Title")
        section2 = parser.extract_section(content, "main title")
        section3 = parser.extract_section(content, "MAIN TITLE")

        assert section1 is not None
        assert section2 is not None
        assert section3 is not None

    def test_extract_nested_section(self):
        """Test extracting a nested section"""
        parser = StructureParser()
        content = """# Main

## Parent

### Nested Target

This is nested content.

### Another Nested"""

        section = parser.extract_section(content, "Nested Target")

        assert section is not None
        assert "### Nested Target" in section
        assert "This is nested content" in section

    def test_extract_nonexistent_section(self):
        """Test extracting a section that doesn't exist"""
        parser = StructureParser()
        content = "# Main\n\nSome content"

        section = parser.extract_section(content, "Nonexistent")

        assert section is None

    def test_extract_first_section(self):
        """Test extracting the first section"""
        parser = StructureParser()
        content = """# First Section

First content.

# Second Section

Second content."""

        section = parser.extract_section(content, "First Section")

        assert section is not None
        assert "First content" in section
        assert "Second Section" not in section


class TestBlockExtraction:
    """Tests for block extraction by ID"""

    def test_extract_block_by_id(self):
        """Test extracting block by ID"""
        parser = StructureParser()
        content = """Paragraph 1

Target paragraph ^target-block

Paragraph 3"""

        block = parser.extract_block(content, "target-block")

        assert block is not None
        assert "Target paragraph" in block
        assert "^target-block" in block

    def test_extract_nonexistent_block(self):
        """Test extracting block that doesn't exist"""
        parser = StructureParser()
        content = "Some content without block IDs"

        block = parser.extract_block(content, "nonexistent")

        assert block is None

    def test_extract_block_from_list(self):
        """Test extracting a list block with ID"""
        parser = StructureParser()
        # Note: Block ID must be at the end of the entire list block
        content = """- Item 1
- Item 2
- Item 3 ^list-item"""

        block = parser.extract_block(content, "list-item")

        assert block is not None
        assert "Item" in block


class TestSectionUpdate:
    """Tests for section content updates"""

    def test_update_section_content(self):
        """Test updating section content"""
        parser = StructureParser()
        content = """# Main

## Section to Update

Old content here.

## Other Section

Leave this alone."""

        new_content = "New content goes here."
        updated = parser.update_section(content, "Section to Update", new_content)

        assert "New content goes here" in updated
        assert "Old content here" not in updated
        assert "## Section to Update" in updated
        assert "Leave this alone" in updated

    def test_update_section_preserves_heading(self):
        """Test that section update preserves the heading line"""
        parser = StructureParser()
        content = """# Main

## Target

Old content."""

        updated = parser.update_section(content, "Target", "New content")

        assert "## Target" in updated
        assert "New content" in updated

    def test_update_nonexistent_section_raises_error(self):
        """Test updating nonexistent section raises ValueError"""
        parser = StructureParser()
        content = "# Main\n\nContent"

        with pytest.raises(ValueError, match="Section not found"):
            parser.update_section(content, "Nonexistent", "New content")


class TestBlockUpdate:
    """Tests for block content updates"""

    def test_update_block_content(self):
        """Test updating block content"""
        parser = StructureParser()
        content = """Paragraph 1

Old block content ^block-1

Paragraph 3"""

        updated = parser.update_block(content, "block-1", "New block content ^block-1")

        assert "New block content" in updated
        assert "Old block content" not in updated
        assert "^block-1" in updated

    def test_update_block_preserves_id(self):
        """Test that block update preserves block ID"""
        parser = StructureParser()
        content = "Original content ^my-block"

        updated = parser.update_block(content, "my-block", "New content")

        assert "New content" in updated
        assert "^my-block" in updated

    def test_update_nonexistent_block_raises_error(self):
        """Test updating nonexistent block raises ValueError"""
        parser = StructureParser()
        content = "Some content without IDs"

        with pytest.raises(ValueError, match="Block not found"):
            parser.update_block(content, "nonexistent", "New content")


class TestWordCount:
    """Tests for word count calculation"""

    def test_basic_word_count(self):
        """Test basic word counting"""
        parser = StructureParser()
        content = "This is a simple sentence with eight words total."

        structure = parser.parse_structure(content)

        assert structure.word_count == 9  # "total" makes it 9

    def test_word_count_excludes_code_blocks(self):
        """Test that code blocks are excluded from word count"""
        parser = StructureParser()
        content = """Hello world

```python
def function():
    pass
```

Goodbye world"""

        structure = parser.parse_structure(content)

        # Should count "Hello world Goodbye world" = 4 words
        assert structure.word_count == 4

    def test_word_count_excludes_inline_code(self):
        """Test that inline code is excluded"""
        parser = StructureParser()
        content = "Use the `print()` function to display text"

        structure = parser.parse_structure(content)

        # "print()" should be excluded
        # "Use the function to display text" = 6 words
        assert structure.word_count == 6


class TestReadingTime:
    """Tests for reading time calculation"""

    def test_reading_time_calculation(self):
        """Test reading time is calculated at 250 WPM"""
        parser = StructureParser()
        # 250 words should be 1 minute
        words = " ".join(["word"] * 250)

        structure = parser.parse_structure(words)

        assert structure.reading_time_minutes == 1.0

    def test_reading_time_rounds_properly(self):
        """Test reading time rounds to 1 decimal place"""
        parser = StructureParser()
        # 125 words = 0.5 minutes
        words = " ".join(["word"] * 125)

        structure = parser.parse_structure(words)

        assert structure.reading_time_minutes == 0.5

    def test_zero_reading_time_for_empty(self):
        """Test zero reading time for empty content"""
        parser = StructureParser()
        content = ""

        structure = parser.parse_structure(content)

        assert structure.reading_time_minutes == 0


class TestDocumentStructure:
    """Tests for complete document structure parsing"""

    def test_complete_document_structure(self):
        """Test parsing a complete document with all elements"""
        parser = StructureParser()
        content = """# Main Document

This is the introduction. ^intro

## Section 1

```python
code here
```

- List item 1
- List item 2 ^list-block

## Section 2

> A quote

Final paragraph. ^final"""

        structure = parser.parse_structure(content)

        # Check headings
        assert len(structure.headings) >= 1

        # Check blocks
        assert len(structure.blocks) > 0

        # Check block refs (intro, list-block, final)
        assert "intro" in structure.block_refs
        assert "list-block" in structure.block_refs
        assert "final" in structure.block_refs

        # Check TOC
        assert len(structure.toc) >= 3

        # Check word count (non-zero)
        assert structure.word_count > 0

        # Check reading time
        assert structure.reading_time_minutes >= 0

    def test_structure_to_dict(self):
        """Test converting structure to dictionary"""
        parser = StructureParser()
        content = "# Test\n\nContent here ^block1"

        structure = parser.parse_structure(content)
        result = structure.to_dict()

        assert isinstance(result, dict)
        assert 'headings' in result
        assert 'blocks' in result
        assert 'block_refs' in result
        assert 'toc' in result
        assert 'word_count' in result
        assert 'reading_time_minutes' in result
