"""
Shared pytest fixtures for Obsidian MCP tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from app.vault.parser import MarkdownParser
from app.vault.manager import VaultManager


@pytest.fixture
def temp_vault_path(tmp_path):
    """Create a temporary vault directory"""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    yield vault_path
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def sample_notes() -> Dict[str, str]:
    """Sample note content for testing"""
    return {
        "Welcome.md": """---
title: Welcome
tags: [meta, index]
---

# Welcome to the Test Vault

This is a test vault for [[Projects]] and [[Ideas]].

See also: [[Getting Started]]
""",
        "Projects.md": """---
title: Projects
tags: [work, active]
---

# Active Projects

## Project Alpha
Working on [[Feature Development]] for the new system.

## Project Beta
Collaborating with [[Team]] on [[Research]].
""",
        "Ideas.md": """---
title: Ideas
tags: [brainstorm, creative]
---

# Random Ideas

- Build a [[Knowledge Graph]]
- Explore [[Machine Learning]]
- Document [[Best Practices]]

#innovation #future
""",
        "Getting Started.md": """---
title: Getting Started
tags: [guide, tutorial]
---

# Getting Started Guide

Welcome! Check out [[Projects]] to see what's happening.

For more info, see the [[Documentation]].
""",
        "Feature Development.md": """---
title: Feature Development
tags: [engineering, development]
created: 2025-01-15
---

# Feature Development Process

Our approach to building features.

Related: [[Projects]], [[Best Practices]]
""",
        "Team.md": """---
title: Team
tags: [people, collaboration]
---

# Team Members

Working together on [[Projects]].
""",
        "Orphan Note.md": """---
title: Orphan Note
tags: [isolated]
---

# This note has no backlinks

It's completely isolated from the rest of the vault.
""",
        "subfolder/Nested Note.md": """---
title: Nested Note
tags: [organization]
---

# Nested Note

This note is in a subfolder. Links to [[Welcome]].
"""
    }


@pytest.fixture
def populated_vault(temp_vault_path, sample_notes):
    """Create a vault populated with sample notes"""
    # Create subfolder
    (temp_vault_path / "subfolder").mkdir(exist_ok=True)

    # Write all sample notes
    for filename, content in sample_notes.items():
        filepath = temp_vault_path / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding='utf-8')

    return temp_vault_path


@pytest.fixture
def parser(populated_vault):
    """Create a MarkdownParser instance with populated vault"""
    return MarkdownParser(populated_vault)


@pytest.fixture
def vault_manager(populated_vault, monkeypatch):
    """Create a VaultManager instance with populated vault"""
    # Mock settings to use test vault path
    from app import config
    from app.config import Settings

    # Create test settings instance
    test_settings = Settings(
        obsidian_vault_path=str(populated_vault),
        mcp_api_key="test-api-key-1234567890"
    )
    monkeypatch.setattr(config, 'settings', test_settings)
    return VaultManager()


@pytest.fixture
def empty_vault_manager(temp_vault_path, monkeypatch):
    """Create a VaultManager instance with empty vault"""
    # Mock settings to use test vault path
    from app import config
    from app.config import Settings

    # Create test settings instance
    test_settings = Settings(
        obsidian_vault_path=str(temp_vault_path),
        mcp_api_key="test-api-key-1234567890"
    )
    monkeypatch.setattr(config, 'settings', test_settings)
    return VaultManager()


@pytest.fixture
def sample_frontmatter() -> Dict[str, Any]:
    """Sample frontmatter for testing"""
    return {
        "title": "Test Note",
        "tags": ["test", "example"],
        "created": "2025-12-29",
        "author": "Test User"
    }


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content for testing"""
    return """# Test Note

This is a test note with [[wiki-links]] and #tags.

## Section 1

Some content here linking to [[Another Note]].

## Section 2

More content with [[Yet Another Note|an alias]].
"""


@pytest.fixture
def daily_note_dates():
    """Sample dates for daily note testing"""
    return [
        "2025-12-29",
        "2025-01-01",
        "2024-12-31"
    ]


# API Testing Fixtures

@pytest.fixture
def api_key():
    """Test API key"""
    return "test-api-key-12345"


@pytest.fixture
def auth_headers(api_key):
    """Authentication headers for API tests"""
    return {
        "Authorization": f"Bearer {api_key}"
    }


# Mock data for MCP testing

@pytest.fixture
def mcp_create_note_args():
    """Sample MCP create_note arguments"""
    return {
        "title": "Test Note",
        "content": "This is a test note content.",
        "tags": ["test", "example"]
    }


@pytest.fixture
def mcp_search_args():
    """Sample MCP search_notes arguments"""
    return {
        "query": "test",
        "tags": ["example"],
        "limit": 50,
        "use_regex": False
    }


@pytest.fixture
def mcp_list_args():
    """Sample MCP list_notes arguments"""
    return {
        "directory": "",
        "recursive": True,
        "include_frontmatter": False,
        "limit": 100,
        "offset": 0,
        "sort_by": "modified"
    }
