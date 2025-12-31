"""
Unit tests for template system

Tests for template parsing, rendering, and management.
"""

import pytest
from pathlib import Path
from datetime import datetime
from app.vault.templates import (
    TemplateParser,
    TemplateRenderer,
    TemplateManager,
    Template,
    TemplateRenderResult
)


class TestTemplateParser:
    """Tests for TemplateParser class"""

    @pytest.fixture
    def parser(self):
        return TemplateParser()

    def test_parse_simple_template(self, parser):
        """Test parsing a simple template with variables"""
        content = "# {{title}}\n\nContent: {{body}}"
        template = parser.parse(content, "test")

        assert template.name == "test"
        assert template.variables == {"title", "body"}
        assert template.extends is None
        assert template.includes == []

    def test_parse_template_with_extends(self, parser):
        """Test parsing template with extends directive"""
        content = '{% extends "base" %}\n\n# {{title}}'
        template = parser.parse(content, "child")

        assert template.extends == "base"
        assert template.variables == {"title"}

    def test_parse_template_with_includes(self, parser):
        """Test parsing template with include directives"""
        content = '{% include "header" %}\n\nContent\n\n{% include "footer" %}'
        template = parser.parse(content, "test")

        assert template.includes == ["header", "footer"]

    def test_parse_template_with_date_macro(self, parser):
        """Test parsing template with built-in date macro"""
        content = "Date: {{date}}"
        template = parser.parse(content, "test")

        # Built-in macros should not be in variables list
        assert "date" not in template.variables
        assert template.variables == set()

    def test_parse_template_with_time_macro(self, parser):
        """Test parsing template with built-in time macro"""
        content = "Time: {{time}}"
        template = parser.parse(content, "test")

        assert "time" not in template.variables
        assert template.variables == set()

    def test_parse_template_with_datetime_macro(self, parser):
        """Test parsing template with built-in datetime macro"""
        content = "DateTime: {{datetime}}"
        template = parser.parse(content, "test")

        assert "datetime" not in template.variables
        assert template.variables == set()

    def test_parse_template_with_format_specifier(self, parser):
        """Test parsing template with format specifier"""
        content = "Date: {{date:%Y-%m-%d}}"
        template = parser.parse(content, "test")

        assert "date" not in template.variables

    def test_parse_mixed_variables_and_macros(self, parser):
        """Test parsing template with both variables and macros"""
        content = "# {{title}}\n\nDate: {{date}}\nAuthor: {{author}}"
        template = parser.parse(content, "test")

        assert template.variables == {"title", "author"}
        assert "date" not in template.variables

    def test_extract_variables(self, parser):
        """Test extracting variables from content"""
        content = "{{var1}} and {{var2}} but not {{date}}"
        variables = parser.extract_variables(content)

        assert variables == {"var1", "var2"}
        assert "date" not in variables

    def test_parse_template_no_variables(self, parser):
        """Test parsing template with no variables"""
        content = "# Static Content\n\nNo variables here."
        template = parser.parse(content, "static")

        assert template.variables == set()
        assert template.extends is None
        assert template.includes == []

    def test_parse_complex_template(self, parser):
        """Test parsing complex template with all features"""
        content = '''{% extends "base" %}

# {{title}}

{% include "header" %}

**Date:** {{date}}
**Author:** {{author}}
**Project:** {{project}}

{% include "footer" %}
'''
        template = parser.parse(content, "complex")

        assert template.extends == "base"
        assert template.includes == ["header", "footer"]
        assert template.variables == {"title", "author", "project"}
        assert "date" not in template.variables


class TestTemplateRenderer:
    """Tests for TemplateRenderer class"""

    @pytest.fixture
    def renderer(self):
        return TemplateRenderer()

    def test_render_simple_variable(self, renderer):
        """Test rendering simple variable substitution"""
        content = "Hello {{name}}"
        result = renderer.render(content, {"name": "World"})

        assert result.content == "Hello World"
        assert "name" in result.variables_used
        assert result.variables_missing == []

    def test_render_multiple_variables(self, renderer):
        """Test rendering multiple variables"""
        content = "{{greeting}} {{name}}!"
        result = renderer.render(content, {"greeting": "Hello", "name": "World"})

        assert result.content == "Hello World!"
        assert set(result.variables_used) == {"greeting", "name"}
        assert result.variables_missing == []

    def test_render_missing_variable(self, renderer):
        """Test rendering with missing variable"""
        content = "Hello {{name}}"
        result = renderer.render(content, {})

        assert result.content == "Hello {{name}}"
        assert result.variables_used == []
        assert "name" in result.variables_missing

    def test_render_date_macro(self, renderer):
        """Test rendering date macro"""
        content = "Date: {{date}}"
        result = renderer.render(content, {})

        # Check that date is in YYYY-MM-DD format
        assert "Date:" in result.content
        assert len(result.content.split(": ")[1]) == 10  # YYYY-MM-DD
        assert "date" in result.variables_used

    def test_render_time_macro(self, renderer):
        """Test rendering time macro"""
        content = "Time: {{time}}"
        result = renderer.render(content, {})

        # Check that time is in HH:MM:SS format
        assert "Time:" in result.content
        assert "time" in result.variables_used

    def test_render_datetime_macro(self, renderer):
        """Test rendering datetime macro"""
        content = "DateTime: {{datetime}}"
        result = renderer.render(content, {})

        # Check that datetime is present
        assert "DateTime:" in result.content
        assert "datetime" in result.variables_used

    def test_render_date_with_format(self, renderer):
        """Test rendering date with custom format"""
        content = "Date: {{date:%B %d, %Y}}"
        result = renderer.render(content, {})

        # Check that date is formatted
        assert "Date:" in result.content
        assert "date" in result.variables_used
        # Format should be like "December 30, 2025"
        assert "," in result.content

    def test_render_mixed_variables_and_macros(self, renderer):
        """Test rendering mixed variables and macros"""
        content = "# {{title}}\n\nDate: {{date}}\nAuthor: {{author}}"
        result = renderer.render(content, {"title": "Report", "author": "John"})

        assert "# Report" in result.content
        assert "Author: John" in result.content
        assert "Date: 2025" in result.content
        assert set(result.variables_used) == {"title", "author", "date"}

    def test_render_duplicate_variables(self, renderer):
        """Test rendering with duplicate variable usage"""
        content = "{{name}} and {{name}} again"
        result = renderer.render(content, {"name": "Test"})

        assert result.content == "Test and Test again"
        # Should only appear once in variables_used
        assert result.variables_used.count("name") == 1

    def test_render_no_variables(self, renderer):
        """Test rendering static content with no variables"""
        content = "Static content"
        result = renderer.render(content, {})

        assert result.content == "Static content"
        assert result.variables_used == []
        assert result.variables_missing == []

    def test_render_empty_content(self, renderer):
        """Test rendering empty content"""
        result = renderer.render("", {})

        assert result.content == ""
        assert result.variables_used == []
        assert result.variables_missing == []


class TestTemplateManager:
    """Tests for TemplateManager class"""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create a temporary vault directory"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        return vault_path

    @pytest.fixture
    def manager(self, temp_vault):
        """Create TemplateManager instance"""
        return TemplateManager(temp_vault)

    def test_init_creates_templates_directory(self, temp_vault):
        """Test that initialization creates .templates directory"""
        manager = TemplateManager(temp_vault)

        assert (temp_vault / ".templates").exists()
        assert (temp_vault / ".templates").is_dir()

    def test_save_template(self, manager, temp_vault):
        """Test saving a template"""
        content = "# {{title}}\n\nContent: {{body}}"
        success = manager.save_template("test", content)

        assert success
        template_path = temp_vault / ".templates" / "test.md"
        assert template_path.exists()
        assert template_path.read_text() == content

    def test_save_template_invalid_name(self, manager):
        """Test saving template with invalid name (path traversal)"""
        with pytest.raises(ValueError, match="Invalid template name"):
            manager.save_template("../evil", "content")

        with pytest.raises(ValueError, match="Invalid template name"):
            manager.save_template("sub/dir", "content")

    def test_get_template(self, manager, temp_vault):
        """Test retrieving a template"""
        content = "# {{title}}"
        manager.save_template("test", content)

        template = manager.get_template("test")

        assert template is not None
        assert template.name == "test"
        assert template.content == content
        assert template.variables == {"title"}

    def test_get_nonexistent_template(self, manager):
        """Test retrieving non-existent template"""
        template = manager.get_template("nonexistent")

        assert template is None

    def test_list_templates_empty(self, manager):
        """Test listing templates when none exist"""
        templates = manager.list_templates()

        assert templates == []

    def test_list_templates(self, manager):
        """Test listing multiple templates"""
        manager.save_template("template1", "# {{title}}")
        manager.save_template("template2", "# {{name}}\n{{date}}")

        templates = manager.list_templates()

        assert len(templates) == 2
        assert any(t["name"] == "template1" for t in templates)
        assert any(t["name"] == "template2" for t in templates)

        # Check template1 metadata
        t1 = next(t for t in templates if t["name"] == "template1")
        assert t1["variables"] == ["title"]
        assert t1["extends"] is None
        assert t1["includes"] == []

    def test_delete_template(self, manager, temp_vault):
        """Test deleting a template"""
        manager.save_template("test", "content")
        assert (temp_vault / ".templates" / "test.md").exists()

        success = manager.delete_template("test")

        assert success
        assert not (temp_vault / ".templates" / "test.md").exists()

    def test_delete_nonexistent_template(self, manager):
        """Test deleting non-existent template"""
        success = manager.delete_template("nonexistent")

        assert not success

    def test_render_template(self, manager):
        """Test rendering a template"""
        manager.save_template("test", "# {{title}}\n\nAuthor: {{author}}")

        result = manager.render_template("test", {"title": "Report", "author": "John"})

        assert "# Report" in result.content
        assert "Author: John" in result.content
        assert result.variables_missing == []

    def test_render_template_with_missing_variables(self, manager):
        """Test rendering template with missing variables"""
        manager.save_template("test", "# {{title}}")

        result = manager.render_template("test", {})

        assert "{{title}}" in result.content
        assert "title" in result.variables_missing

    def test_render_nonexistent_template(self, manager):
        """Test rendering non-existent template raises error"""
        with pytest.raises(ValueError, match="Template not found"):
            manager.render_template("nonexistent", {})

    def test_render_template_with_extends(self, manager):
        """Test rendering template with inheritance"""
        # Create base template
        manager.save_template("base", "BASE CONTENT\n\n---\n\n")

        # Create child template
        manager.save_template("child", '{% extends "base" %}\n\nCHILD CONTENT')

        result = manager.render_template("child", {})

        assert "BASE CONTENT" in result.content
        assert "CHILD CONTENT" in result.content

    def test_render_template_with_includes(self, manager):
        """Test rendering template with includes"""
        # Create included templates
        manager.save_template("header", "=== HEADER ===")
        manager.save_template("footer", "=== FOOTER ===")

        # Create main template
        manager.save_template(
            "main",
            '{% include "header" %}\n\nMAIN CONTENT\n\n{% include "footer" %}'
        )

        result = manager.render_template("main", {})

        assert "=== HEADER ===" in result.content
        assert "MAIN CONTENT" in result.content
        assert "=== FOOTER ===" in result.content

    def test_render_template_max_depth(self, manager):
        """Test that template recursion is limited"""
        # Create circular reference
        manager.save_template("a", '{% extends "b" %}')
        manager.save_template("b", '{% extends "c" %}')
        manager.save_template("c", '{% extends "d" %}')
        manager.save_template("d", '{% extends "e" %}')
        manager.save_template("e", '{% extends "f" %}')
        manager.save_template("f", '{% extends "g" %}')  # Exceeds MAX_DEPTH of 5

        with pytest.raises(ValueError, match="too deep"):
            manager.render_template("a", {})

    def test_create_note_from_template(self, manager):
        """Test creating note content from template"""
        manager.save_template("meeting", "# {{title}}\n\nDate: {{date}}")

        content = manager.create_note_from_template(
            "meeting",
            {"title": "Team Sync"}
        )

        assert "# Team Sync" in content
        assert "Date: 2025" in content

    def test_create_note_from_nonexistent_template(self, manager):
        """Test creating note from non-existent template raises error"""
        with pytest.raises(ValueError, match="Template not found"):
            manager.create_note_from_template("nonexistent", {})

    def test_template_with_complex_variables(self, manager):
        """Test template with complex variable names"""
        manager.save_template(
            "complex",
            "{{var_1}} {{var_2}} {{VarName}} {{snake_case_var}}"
        )

        result = manager.render_template(
            "complex",
            {
                "var_1": "A",
                "var_2": "B",
                "VarName": "C",
                "snake_case_var": "D"
            }
        )

        assert result.content == "A B C D"
        assert len(result.variables_missing) == 0


# Integration tests
class TestTemplateIntegration:
    """Integration tests for complete template workflows"""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        return vault_path

    @pytest.fixture
    def manager(self, temp_vault):
        return TemplateManager(temp_vault)

    def test_full_workflow_simple_template(self, manager):
        """Test complete workflow: save, list, render"""
        # Save template
        manager.save_template("note", "# {{title}}\n\n{{content}}")

        # List templates
        templates = manager.list_templates()
        assert len(templates) == 1
        assert templates[0]["name"] == "note"
        assert sorted(templates[0]["variables"]) == ["content", "title"]

        # Render template
        content = manager.create_note_from_template(
            "note",
            {"title": "My Note", "content": "Note content"}
        )
        assert "# My Note" in content
        assert "Note content" in content

    def test_full_workflow_with_inheritance(self, manager):
        """Test complete workflow with template inheritance"""
        # Create base template
        manager.save_template(
            "base",
            "---\nlayout: {{layout}}\n---\n\nBASE HEADER\n\n"
        )

        # Create child template
        manager.save_template(
            "article",
            '{% extends "base" %}\n\n# {{title}}\n\nby {{author}}'
        )

        # Render
        content = manager.create_note_from_template(
            "article",
            {"layout": "default", "title": "Article Title", "author": "John Doe"}
        )

        assert "layout: default" in content
        assert "BASE HEADER" in content
        assert "# Article Title" in content
        assert "by John Doe" in content

    def test_full_workflow_with_date_macros(self, manager):
        """Test complete workflow with date macros"""
        manager.save_template(
            "journal",
            "# Journal Entry\n\n**Date:** {{date}}\n**Time:** {{time}}\n\n{{entry}}"
        )

        content = manager.create_note_from_template(
            "journal",
            {"entry": "Today was great!"}
        )

        assert "# Journal Entry" in content
        assert "**Date:** 2025-" in content
        assert "**Time:**" in content
        assert "Today was great!" in content
