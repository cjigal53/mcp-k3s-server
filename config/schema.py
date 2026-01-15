"""Configuration schema definitions for the application.

This module defines the schema for configuration validation,
including required fields, field types, and custom validators.
"""

from typing import Any, Dict, List, Optional


# Default required fields for application configuration
DEFAULT_REQUIRED_FIELDS: List[str] = []

# Default field type mappings
DEFAULT_FIELD_TYPES: Dict[str, type] = {}


def validate_port(value: Any) -> bool:
    """Validate that a value is a valid port number.

    Args:
        value: Value to validate.

    Returns:
        True if valid, error message string if invalid.
    """
    if not isinstance(value, int):
        return "Port must be an integer"
    if not (1 <= value <= 65535):
        return "Port must be between 1 and 65535"
    return True


def validate_log_level(value: Any) -> bool:
    """Validate that a value is a valid log level.

    Args:
        value: Value to validate.

    Returns:
        True if valid, error message string if invalid.
    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if not isinstance(value, str):
        return "Log level must be a string"
    if value.upper() not in valid_levels:
        return f"Log level must be one of: {', '.join(valid_levels)}"
    return True


def validate_positive_integer(value: Any) -> bool:
    """Validate that a value is a positive integer.

    Args:
        value: Value to validate.

    Returns:
        True if valid, error message string if invalid.
    """
    if not isinstance(value, int):
        return "Value must be an integer"
    if value <= 0:
        return "Value must be positive"
    return True


def validate_non_empty_string(value: Any) -> bool:
    """Validate that a value is a non-empty string.

    Args:
        value: Value to validate.

    Returns:
        True if valid, error message string if invalid.
    """
    if not isinstance(value, str):
        return "Value must be a string"
    if not value.strip():
        return "Value cannot be empty"
    return True


# Default custom validators
DEFAULT_CUSTOM_VALIDATORS: Dict[str, callable] = {}


def get_schema(
    required_fields: Optional[List[str]] = None,
    field_types: Optional[Dict[str, type]] = None,
    custom_validators: Optional[Dict[str, callable]] = None,
) -> Dict[str, Any]:
    """Get a configuration schema with optional overrides.

    Args:
        required_fields: Override for required fields.
        field_types: Override for field types.
        custom_validators: Override for custom validators.

    Returns:
        Dictionary containing schema configuration.
    """
    return {
        "required_fields": required_fields or DEFAULT_REQUIRED_FIELDS.copy(),
        "field_types": field_types or DEFAULT_FIELD_TYPES.copy(),
        "custom_validators": custom_validators or DEFAULT_CUSTOM_VALIDATORS.copy(),
    }
