import logging
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TemplateError(Exception):
    """Exception raised for template-related errors."""

    def __init__(self, message: str, template_name: Optional[str] = None):
        """Initialize TemplateError.

        Args:
            message: Error description
            template_name: Name of template that caused the error
        """
        self.template_name = template_name
        if template_name:
            super().__init__(f"Template error in '{template_name}': {message}")
        else:
            super().__init__(f"Template error: {message}")


class TemplateManager:
    """Manager for loading and formatting prompt templates."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize TemplateManager.

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = Path(template_dir) if template_dir else None

    def load_templates(self, template_dir: str) -> Dict[str, str]:
        """Load all templates from directory.

        Args:
            template_dir: Directory path containing template files

        Returns:
            Dictionary mapping template names to template content

        Raises:
            TemplateError: If directory doesn't exist or templates can't be loaded

        Example:
            >>> manager = TemplateManager()
            >>> templates = manager.load_templates("prompts/tower_of_hanoi/")
            >>> print(templates["system"])
        """
        template_path = Path(template_dir)

        if not template_path.exists():
            raise TemplateError(f"Template directory '{template_dir}' does not exist")

        if not template_path.is_dir():
            raise TemplateError(f"Template path '{template_dir}' is not a directory")

        templates = {}
        template_files = list(template_path.glob("*.txt"))

        if not template_files:
            raise TemplateError(f"No template files found in '{template_dir}'")

        for template_file in template_files:
            try:
                template_name = template_file.stem  # Filename without .txt extension
                template_content = template_file.read_text(encoding="utf-8")

                templates[template_name] = template_content
                logger.debug(f"Loaded template '{template_name}' from {template_file}")

            except Exception as e:
                raise TemplateError(
                    f"Failed to load template from '{template_file}': {e}",
                    template_file.stem
                ) from e

        logger.info(f"Loaded {len(templates)} templates from {template_dir}")
        return templates

    def format_template(self, template: str, **kwargs) -> str:
        """Format template with provided variables.

        Args:
            template: Template string with {variable} placeholders
            **kwargs: Variables to substitute in template

        Returns:
            Formatted template string
        """
        try:
            formatted = template.format(**kwargs)
            logger.debug(f"Formatted template with {len(kwargs)} variables")
            return formatted

        except KeyError as e:
            missing_var = str(e).strip("'\"")
            raise TemplateError(f"Missing required variable: {missing_var}") from e

        except Exception as e:
            raise TemplateError(f"Template formatting failed: {e}") from e

    def validate_template_vars(
        self, template: str, required_vars: List[str]
    ) -> List[str]:
        """Validate that template contains all required variables.

        Args:
            template: Template string to validate
            required_vars: List of variable names that must be present

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        try:
            # Extract variables from template using regex
            template_vars = self._extract_template_vars(template)

            # Check for missing required variables
            missing_vars = set(required_vars) - template_vars
            if missing_vars:
                for var in sorted(missing_vars):
                    errors.append(f"Missing required variable: {var}")

            # Check for invalid variable syntax
            syntax_errors = self._validate_template_syntax(template)
            errors.extend(syntax_errors)

        except Exception as e:
            errors.append(f"Template validation failed: {e}")

        logger.debug(f"Template validation found {len(errors)} errors")
        return errors

    def _extract_template_vars(self, template: str) -> Set[str]:
        """Extract variable names from template string.

        Args:
            template: Template string

        Returns:
            Set of variable names found in template
        """
        # Find all {variable} patterns
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, template)

        # Extract variable names (handle format specs like {var:02d})
        variables = set()
        for match in matches:
            # Split on ':' to handle format specifications
            var_name = match.split(":")[0].strip()
            if var_name:  # Ignore empty variable names
                variables.add(var_name)

        return variables

    def _validate_template_syntax(self, template: str) -> List[str]:
        """Validate template syntax for common errors.

        Args:
            template: Template string to validate

        Returns:
            List of syntax error messages
        """
        errors = []

        # Check for unmatched braces
        open_braces = template.count("{")
        close_braces = template.count("}")
        if open_braces != close_braces:
            errors.append(f"Unmatched braces: {open_braces} open, {close_braces} close")

        # Check for empty variable names
        if "{}" in template:
            errors.append("Empty variable placeholder found: {}")

        # Check for nested braces (not supported by str.format)
        if "{{" in template and "}}" in template:
            # This is actually valid (escaped braces), but check for mixed usage
            pass
        elif re.search(r"\{[^}]*\{", template) or re.search(r"\}[^{]*\}", template):
            errors.append("Invalid nested braces detected")

        return errors


def load_templates(template_dir: str) -> Dict[str, str]:
    """Load all templates from directory (convenience function).

    Args:
        template_dir: Directory path containing template files

    Returns:
        Dictionary mapping template names to template content

    Raises:
        TemplateError: If templates cannot be loaded

    Example:
        >>> templates = load_templates("prompts/tower_of_hanoi/")
        >>> system_prompt = templates["system"]
    """
    manager = TemplateManager()
    return manager.load_templates(template_dir)


def format_template(template: str, **kwargs) -> str:
    """Format template with variables (convenience function).

    Args:
        template: Template string with {variable} placeholders
        **kwargs: Variables to substitute in template

    Returns:
        Formatted template string

    Raises:
        TemplateError: If template formatting fails

    Example:
        >>> result = format_template("Hello {name}!", name="World")
        >>> print(result)
        Hello World!
    """
    manager = TemplateManager()
    return manager.format_template(template, **kwargs)


