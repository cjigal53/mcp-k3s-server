"""Configuration validation module for validating YAML/JSON config files.

This module provides functionality to:
- Validate YAML/JSON syntax
- Check required fields
- Provide helpful error messages
- Support environment variable substitution
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        """Initialize ConfigValidationError.

        Args:
            message: Main error message.
            errors: List of specific validation errors.
        """
        self.message = message
        self.errors = errors or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with all validation errors."""
        if not self.errors:
            return self.message
        error_list = "\n  - ".join(self.errors)
        return f"{self.message}\n  - {error_list}"


class ConfigValidator:
    """Validator for configuration files with support for YAML and JSON."""

    ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')

    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        field_types: Optional[Dict[str, type]] = None,
        custom_validators: Optional[Dict[str, callable]] = None,
    ):
        """Initialize ConfigValidator.

        Args:
            required_fields: List of required field paths (dot notation supported).
            field_types: Dictionary mapping field paths to expected types.
            custom_validators: Dictionary mapping field paths to validation functions.
        """
        self.required_fields = required_fields or []
        self.field_types = field_types or {}
        self.custom_validators = custom_validators or {}

    def load_config(
        self,
        config_path: Union[str, Path],
        substitute_env_vars: bool = True,
    ) -> Dict[str, Any]:
        """Load and validate a configuration file.

        Args:
            config_path: Path to the configuration file.
            substitute_env_vars: Whether to substitute environment variables.

        Returns:
            Validated configuration dictionary.

        Raises:
            ConfigValidationError: If validation fails.
            FileNotFoundError: If config file doesn't exist.
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        content = config_path.read_text(encoding='utf-8')

        if substitute_env_vars:
            content = self._substitute_env_vars(content)

        config = self._parse_config(content, config_path)

        self.validate(config)

        return config

    def _parse_config(self, content: str, config_path: Path) -> Dict[str, Any]:
        """Parse configuration content based on file extension.

        Args:
            content: Configuration file content.
            config_path: Path to the configuration file.

        Returns:
            Parsed configuration dictionary.

        Raises:
            ConfigValidationError: If parsing fails.
        """
        suffix = config_path.suffix.lower()

        try:
            if suffix in ('.yaml', '.yml'):
                if not YAML_AVAILABLE:
                    raise ConfigValidationError(
                        "YAML support not available. Install PyYAML: pip install pyyaml"
                    )
                return yaml.safe_load(content) or {}
            elif suffix == '.json':
                return json.loads(content) if content.strip() else {}
            else:
                try:
                    return json.loads(content) if content.strip() else {}
                except json.JSONDecodeError:
                    if YAML_AVAILABLE:
                        return yaml.safe_load(content) or {}
                    raise
        except yaml.YAMLError as e:
            raise ConfigValidationError(
                f"Invalid YAML syntax in {config_path}",
                errors=[str(e)]
            )
        except json.JSONDecodeError as e:
            raise ConfigValidationError(
                f"Invalid JSON syntax in {config_path}",
                errors=[f"Line {e.lineno}, Column {e.colno}: {e.msg}"]
            )

    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in configuration content.

        Supports syntax:
        - ${VAR_NAME} - Required variable
        - ${VAR_NAME:default} - Variable with default value

        Args:
            content: Configuration content with potential env var references.

        Returns:
            Content with environment variables substituted.
        """
        def replace_env_var(match: re.Match) -> str:
            var_name = match.group(1)
            default_value = match.group(2)

            value = os.environ.get(var_name)

            if value is not None:
                return value
            elif default_value is not None:
                return default_value
            else:
                return match.group(0)

        return self.ENV_VAR_PATTERN.sub(replace_env_var, content)

    def validate(self, config: Dict[str, Any]) -> None:
        """Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate.

        Raises:
            ConfigValidationError: If validation fails.
        """
        errors = []

        errors.extend(self._check_required_fields(config))
        errors.extend(self._check_field_types(config))
        errors.extend(self._run_custom_validators(config))

        if errors:
            raise ConfigValidationError("Configuration validation failed", errors=errors)

    def _check_required_fields(self, config: Dict[str, Any]) -> List[str]:
        """Check that all required fields are present.

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages for missing fields.
        """
        errors = []
        for field_path in self.required_fields:
            if not self._field_exists(config, field_path):
                errors.append(f"Missing required field: '{field_path}'")
        return errors

    def _check_field_types(self, config: Dict[str, Any]) -> List[str]:
        """Check that fields have the expected types.

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages for type mismatches.
        """
        errors = []
        for field_path, expected_type in self.field_types.items():
            value = self._get_field_value(config, field_path)
            if value is not None and not isinstance(value, expected_type):
                actual_type = type(value).__name__
                expected_name = expected_type.__name__
                errors.append(
                    f"Field '{field_path}' has wrong type: expected {expected_name}, got {actual_type}"
                )
        return errors

    def _run_custom_validators(self, config: Dict[str, Any]) -> List[str]:
        """Run custom validation functions on fields.

        Args:
            config: Configuration dictionary.

        Returns:
            List of error messages from custom validators.
        """
        errors = []
        for field_path, validator in self.custom_validators.items():
            value = self._get_field_value(config, field_path)
            if value is not None:
                try:
                    result = validator(value)
                    if result is False:
                        errors.append(f"Custom validation failed for field: '{field_path}'")
                    elif isinstance(result, str):
                        errors.append(f"Field '{field_path}': {result}")
                except Exception as e:
                    errors.append(f"Validation error for field '{field_path}': {str(e)}")
        return errors

    def _field_exists(self, config: Dict[str, Any], field_path: str) -> bool:
        """Check if a field exists in the configuration.

        Args:
            config: Configuration dictionary.
            field_path: Dot-notation path to the field.

        Returns:
            True if field exists, False otherwise.
        """
        return self._get_field_value(config, field_path) is not None

    def _get_field_value(
        self, config: Dict[str, Any], field_path: str
    ) -> Optional[Any]:
        """Get a field value from nested configuration using dot notation.

        Args:
            config: Configuration dictionary.
            field_path: Dot-notation path to the field (e.g., 'database.host').

        Returns:
            Field value if found, None otherwise.
        """
        parts = field_path.split('.')
        current = config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current


def validate_config_on_startup(
    config_path: Union[str, Path],
    required_fields: Optional[List[str]] = None,
    field_types: Optional[Dict[str, type]] = None,
    custom_validators: Optional[Dict[str, callable]] = None,
    substitute_env_vars: bool = True,
) -> Dict[str, Any]:
    """Convenience function to validate configuration on application startup.

    Args:
        config_path: Path to the configuration file.
        required_fields: List of required field paths.
        field_types: Dictionary mapping field paths to expected types.
        custom_validators: Dictionary mapping field paths to validation functions.
        substitute_env_vars: Whether to substitute environment variables.

    Returns:
        Validated configuration dictionary.

    Raises:
        ConfigValidationError: If validation fails.
        FileNotFoundError: If config file doesn't exist.
    """
    validator = ConfigValidator(
        required_fields=required_fields,
        field_types=field_types,
        custom_validators=custom_validators,
    )
    return validator.load_config(config_path, substitute_env_vars=substitute_env_vars)
