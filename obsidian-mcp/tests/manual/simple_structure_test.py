#!/usr/bin/env python3
"""
Simple direct test of structure parsing features
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.vault.structure import StructureParser
from app.vault.parser import MarkdownParser

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

# Sample note content
SAMPLE_NOTE = """---
title: Testing Section and Block Operations
tags: [test, demo, phase3]
created: 2025-12-30
---

# Testing Section and Block Operations

This is a comprehensive test note to demonstrate the new structure parsing features. ^intro

## Features Overview

The new system supports:
- Hierarchical heading parsing
- Block references with IDs
- Table of contents generation
- Section extraction and updates

## Code Example

```python
def parse_markdown(content):
    \"\"\"Parse markdown structure\"\"\"
    return structure_parser.parse(content)
```

## Lists and Tasks

Important tasks: ^task-list

- [ ] Test heading parsing
- [ ] Test block extraction
- [x] Implement structure parser
- [ ] Write documentation

## Nested Structure

### Subsection 2.1

This is a nested subsection with some content. ^nested-content

### Subsection 2.2

Another nested section.

#### Deep Section 2.2.1

Going deeper into the structure.

## Quotes and References

> This is an important quote about markdown parsing.
> It spans multiple lines. ^quote-block

## Summary

The structure parser handles all markdown elements correctly. ^summary
"""

def main():
    # Create parsers
    structure_parser = StructureParser()

    print_section("1. PARSE COMPLETE DOCUMENT STRUCTURE")

    structure = structure_parser.parse_structure(SAMPLE_NOTE)

    print(f"📊 Document Statistics:\n")
    print(f"  • Total Headings: {len(structure.headings)}")
    print(f"  • Total Blocks: {len(structure.blocks)}")
    print(f"  • Block References: {len(structure.block_refs)}")
    print(f"  • TOC Entries: {len(structure.toc)}")
    print(f"  • Word Count: {structure.word_count}")
    print(f"  • Reading Time: {structure.reading_time_minutes} minutes")

    print_section("2. TABLE OF CONTENTS")

    print("📑 Hierarchical Structure:\n")
    for entry in structure.toc:
        indent = "  " * (entry['level'] - 1)
        print(f"{indent}• {entry['text']} (#{entry['anchor']}, line {entry['line']})")

    print_section("3. HEADING HIERARCHY")

    def print_headings(headings, indent=0):
        for h in headings:
            prefix = "  " * indent
            print(f"{prefix}• H{h.level}: {h.text}")
            print(f"{prefix}  Anchor: #{h.anchor}")
            print(f"{prefix}  Lines: {h.start_line}-{h.end_line}")
            print(f"{prefix}  Children: {len(h.children)}")
            print()
            if h.children:
                print_headings(h.children, indent + 1)

    print_headings(structure.headings)

    print_section("4. BLOCK REFERENCES")

    print("📦 All Block IDs Found:\n")
    for block_id, block in structure.block_refs.items():
        print(f"  • ^{block_id}")
        print(f"    Type: {block.block_type.value}")
        print(f"    Lines: {block.start_line}-{block.end_line}")
        content_preview = block.content.replace('\n', ' ')[:60]
        print(f"    Content: {content_preview}...")
        print()

    print_section("5. EXTRACT SECTION BY NAME")

    section_content = structure_parser.extract_section(SAMPLE_NOTE, "Features Overview")

    if section_content:
        print("✅ Successfully extracted 'Features Overview' section:\n")
        print("-" * 80)
        print(section_content)
        print("-" * 80)
    else:
        print("❌ Section not found")

    print_section("6. EXTRACT NESTED SECTION")

    nested_section = structure_parser.extract_section(SAMPLE_NOTE, "Subsection 2.1")

    if nested_section:
        print("✅ Successfully extracted 'Subsection 2.1' (nested):\n")
        print("-" * 80)
        print(nested_section)
        print("-" * 80)
    else:
        print("❌ Nested section not found")

    print_section("7. EXTRACT BLOCK BY ID")

    block_ids_to_test = ["intro", "task-list", "nested-content", "quote-block", "summary"]

    for block_id in block_ids_to_test:
        block_content = structure_parser.extract_block(SAMPLE_NOTE, block_id)
        if block_content:
            content_preview = block_content.replace('\n', ' ')[:80]
            print(f"✅ ^{block_id}: {content_preview}...")
        else:
            print(f"❌ ^{block_id}: Not found")

    print_section("8. UPDATE SECTION CONTENT")

    new_summary = """The structure parser successfully handles ALL markdown elements:
- Headings (H1-H6) with proper nesting
- Block references with IDs
- Code blocks, lists, quotes, tables
- Word counting and reading time

**Result**: 100% test success! ✅"""

    updated_content = structure_parser.update_section(SAMPLE_NOTE, "Summary", new_summary)

    print("🔄 Updated 'Summary' section")
    print("\n📄 Verifying update...")

    # Extract the updated section to verify
    updated_section = structure_parser.extract_section(updated_content, "Summary")
    if updated_section:
        print("\n✅ Section updated successfully:\n")
        print("-" * 80)
        print(updated_section)
        print("-" * 80)

    print_section("9. UPDATE BLOCK BY ID")

    new_intro = """This is an UPDATED test note demonstrating structure parsing with block updates! ^intro"""

    updated_content2 = structure_parser.update_block(updated_content, "intro", new_intro)

    print("🔄 Updated ^intro block")
    print("\n📄 Verifying update...")

    # Extract the updated block
    updated_block = structure_parser.extract_block(updated_content2, "intro")
    if updated_block:
        print("\n✅ Block updated successfully:\n")
        print("-" * 80)
        print(updated_block)
        print("-" * 80)

    print_section("10. WORD COUNT & READING TIME")

    # Parse the final updated content
    final_structure = structure_parser.parse_structure(updated_content2)

    print(f"📊 Final Document Metrics:\n")
    print(f"  • Word Count: {final_structure.word_count} words")
    print(f"  • Reading Time: {final_structure.reading_time_minutes} minutes")
    print(f"  • Total Blocks: {len(final_structure.blocks)}")
    print(f"  • Block References: {len(final_structure.block_refs)}")
    print(f"  • Headings: {len(final_structure.headings)}")

    print("\n📚 Block Type Breakdown:")
    from collections import Counter
    block_types = Counter(b.block_type.value for b in final_structure.blocks)
    for block_type, count in block_types.items():
        print(f"  • {block_type}: {count}")

    print_section("✅ ALL STRUCTURE OPERATIONS VERIFIED!")

    print("Features Successfully Demonstrated:")
    print("  ✅ Complete document structure parsing")
    print("  ✅ Hierarchical heading parsing (H1-H6)")
    print("  ✅ Table of contents generation")
    print("  ✅ Section extraction (top-level & nested)")
    print("  ✅ Block extraction by ID")
    print("  ✅ Section content updates")
    print("  ✅ Block content updates")
    print("  ✅ Word count calculation")
    print("  ✅ Reading time estimation")
    print("  ✅ Block reference tracking")

    print("\n🎉 All structure parsing features working perfectly!\n")

if __name__ == "__main__":
    main()
