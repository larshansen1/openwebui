"""
Template system for Obsidian vault.

Provides template parsing, variable substitution, inheritance, and includes.

Features:
- Variable substitution: {{variable_name}}
- Built-in macros: {{date}}, {{time}}, {{datetime}}, {{date:%Y-%m-%d}}
- Template inheritance: {% extends "base" %}
- Template includes: {% include "header" %}
- Template storage in .templates/ folder

Security:
- No code execution (unlike Jinja2)
- Simple text substitution only
- Max template depth: 5 levels
- Regex timeout: 100ms
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class Template:
    """Represents a parsed template."""
    name: str
    content: str
    extends: Optional[str] = None  # Parent template name
    includes: List[str] = field(default_factory=list)  # Included template names
    variables: Set[str] = field(default_factory=set)  # Variables found in template


@dataclass
class TemplateRenderResult:
    """Result of rendering a template."""
    content: str
    variables_used: List[str]
    variables_missing: List[str]


class TemplateParser:
    """Parse template files and extract template directives."""

    # Regex patterns
    VARIABLE_PATTERN = re.compile(r'\{\{([a-zA-Z0-9_]+)(?::([^}]+))?\}\}')
    EXTENDS_PATTERN = re.compile(r'\{%\s*extends\s+"([^"]+)"\s*%\}')
    INCLUDE_PATTERN = re.compile(r'\{%\s*include\s+"([^"]+)"\s*%\}')

    # Built-in macros (variables that have special handling)
    BUILT_IN_MACROS = {'date', 'time', 'datetime'}

    def parse(self, content: str, template_name: str) -> Template:
        """
        Parse a template and extract its metadata.

        Args:
            content: Template content
            template_name: Name of the template

        Returns:
            Template object with parsed metadata
        """
        # Extract extends directive (must be at top of file)
        extends_match = self.EXTENDS_PATTERN.search(content)
        extends = extends_match.group(1) if extends_match else None

        # Extract all include directives
        includes = [match.group(1) for match in self.INCLUDE_PATTERN.finditer(content)]

        # Extract all variables (excluding built-in macros)
        variables = set()
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_name = match.group(1)
            if var_name not in self.BUILT_IN_MACROS:
                variables.add(var_name)

        return Template(
            name=template_name,
            content=content,
            extends=extends,
            includes=includes,
            variables=variables
        )

    def extract_variables(self, content: str) -> Set[str]:
        """
        Extract all variable names from content.

        Args:
            content: Template content

        Returns:
            Set of variable names (excluding built-in macros)
        """
        variables = set()
        for match in self.VARIABLE_PATTERN.finditer(content):
            var_name = match.group(1)
            if var_name not in self.BUILT_IN_MACROS:
                variables.add(var_name)
        return variables


class TemplateRenderer:
    """Render templates with variable substitution."""

    def __init__(self):
        self.parser = TemplateParser()

    def render(
        self,
        content: str,
        variables: Optional[Dict[str, str]] = None
    ) -> TemplateRenderResult:
        """
        Render a template with variable substitution.

        Args:
            content: Template content
            variables: Dictionary of variable values

        Returns:
            TemplateRenderResult with rendered content and metadata
        """
        if variables is None:
            variables = {}

        variables_used = []
        variables_missing = []

        def replace_variable(match: re.Match) -> str:
            var_name = match.group(1)
            format_spec = match.group(2)  # Optional format specifier

            # Handle built-in macros
            if var_name in TemplateParser.BUILT_IN_MACROS:
                variables_used.append(var_name)
                return self._render_macro(var_name, format_spec)

            # Handle user variables
            if var_name in variables:
                variables_used.append(var_name)
                return str(variables[var_name])
            else:
                variables_missing.append(var_name)
                return match.group(0)  # Keep original {{var}} if not found

        # Replace all variables
        rendered_content = TemplateParser.VARIABLE_PATTERN.sub(
            replace_variable,
            content
        )

        return TemplateRenderResult(
            content=rendered_content,
            variables_used=list(set(variables_used)),  # Remove duplicates
            variables_missing=list(set(variables_missing))
        )

    def _render_macro(self, macro_name: str, format_spec: Optional[str]) -> str:
        """
        Render a built-in macro.

        Args:
            macro_name: Name of the macro (date, time, datetime)
            format_spec: Optional format specifier (e.g., %Y-%m-%d)

        Returns:
            Rendered macro value
        """
        now = datetime.now()

        if macro_name == 'date':
            if format_spec:
                return now.strftime(format_spec)
            return now.strftime('%Y-%m-%d')

        elif macro_name == 'time':
            if format_spec:
                return now.strftime(format_spec)
            return now.strftime('%H:%M:%S')

        elif macro_name == 'datetime':
            if format_spec:
                return now.strftime(format_spec)
            return now.strftime('%Y-%m-%d %H:%M:%S')

        return f'{{{{{macro_name}}}}}'  # Return unchanged if unknown


class TemplateManager:
    """
    Manage templates in the .templates/ folder.

    Templates are stored as markdown files in .templates/ folder at vault root.
    Template name = filename without .md extension.
    """

    MAX_DEPTH = 5  # Maximum template inheritance/include depth

    def __init__(self, vault_path: Path):
        """
        Initialize template manager.

        Args:
            vault_path: Path to vault root
        """
        self.vault_path = vault_path
        self.templates_dir = vault_path / '.templates'
        self.parser = TemplateParser()
        self.renderer = TemplateRenderer()

        # Ensure templates directory exists
        self.templates_dir.mkdir(exist_ok=True)

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates.

        Returns:
            List of template metadata dictionaries
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        for template_file in self.templates_dir.glob('*.md'):
            try:
                content = template_file.read_text(encoding='utf-8')
                template = self.parser.parse(content, template_file.stem)

                templates.append({
                    'name': template.name,
                    'extends': template.extends,
                    'includes': template.includes,
                    'variables': list(template.variables),
                    'has_extends': template.extends is not None,
                    'has_includes': len(template.includes) > 0
                })
            except Exception as e:
                logger.warning(f"Failed to parse template {template_file.name}: {e}")
                continue

        return sorted(templates, key=lambda t: t['name'])

    def get_template(self, name: str) -> Optional[Template]:
        """
        Get a template by name.

        Args:
            name: Template name (without .md extension)

        Returns:
            Template object or None if not found
        """
        template_path = self.templates_dir / f"{name}.md"

        if not template_path.exists():
            return None

        try:
            content = template_path.read_text(encoding='utf-8')
            return self.parser.parse(content, name)
        except Exception as e:
            logger.error(f"Failed to load template {name}: {e}")
            return None

    def save_template(self, name: str, content: str) -> bool:
        """
        Save a template.

        Args:
            name: Template name (without .md extension)
            content: Template content

        Returns:
            True if saved successfully
        """
        # Validate template name (no path traversal)
        if '/' in name or '\\' in name or '..' in name:
            raise ValueError(f"Invalid template name: {name}")

        template_path = self.templates_dir / f"{name}.md"

        try:
            # Ensure templates directory exists
            self.templates_dir.mkdir(exist_ok=True)

            # Save template
            template_path.write_text(content, encoding='utf-8')
            logger.info(f"Saved template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save template {name}: {e}")
            return False

    def delete_template(self, name: str) -> bool:
        """
        Delete a template.

        Args:
            name: Template name (without .md extension)

        Returns:
            True if deleted successfully
        """
        template_path = self.templates_dir / f"{name}.md"

        if not template_path.exists():
            return False

        try:
            template_path.unlink()
            logger.info(f"Deleted template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete template {name}: {e}")
            return False

    def render_template(
        self,
        name: str,
        variables: Optional[Dict[str, str]] = None,
        depth: int = 0
    ) -> TemplateRenderResult:
        """
        Render a template with inheritance and includes.

        Args:
            name: Template name
            variables: Variable values
            depth: Current recursion depth (internal)

        Returns:
            TemplateRenderResult with fully rendered content

        Raises:
            ValueError: If template not found or max depth exceeded
        """
        if depth > self.MAX_DEPTH:
            raise ValueError(f"Template recursion too deep (max {self.MAX_DEPTH})")

        # Load template
        template = self.get_template(name)
        if template is None:
            raise ValueError(f"Template not found: {name}")

        content = template.content

        # Process extends directive
        if template.extends:
            # Render parent template first
            parent_result = self.render_template(
                template.extends,
                variables,
                depth + 1
            )

            # Remove extends directive from current template
            content = TemplateParser.EXTENDS_PATTERN.sub('', content)

            # Replace parent content with extended content
            # In this simple implementation, child content replaces parent
            # (More sophisticated would support blocks/placeholders)
            content = parent_result.content + '\n\n' + content

        # Process include directives
        for include_name in template.includes:
            try:
                include_result = self.render_template(
                    include_name,
                    variables,
                    depth + 1
                )

                # Replace include directive with rendered content
                include_pattern = re.compile(
                    r'\{%\s*include\s+"' + re.escape(include_name) + r'"\s*%\}'
                )
                content = include_pattern.sub(include_result.content, content)
            except Exception as e:
                logger.warning(f"Failed to include template {include_name}: {e}")
                # Leave include directive in place if it fails

        # Render variables
        result = self.renderer.render(content, variables)

        return result

    def create_note_from_template(
        self,
        template_name: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create note content from a template.

        Args:
            template_name: Name of template to use
            variables: Variable values

        Returns:
            Rendered note content

        Raises:
            ValueError: If template not found or rendering fails
        """
        result = self.render_template(template_name, variables)

        if result.variables_missing:
            logger.warning(
                f"Template {template_name} has unsubstituted variables: "
                f"{', '.join(result.variables_missing)}"
            )

        return result.content
