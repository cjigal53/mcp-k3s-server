"""Tests for the configuration validator module."""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from core.config_validator import (
    ConfigValidator,
    ConfigValidationError,
    validate_config_on_startup,
)


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_load_json_config(self, tmp_path: Path):
        """Test loading a valid JSON configuration file."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"host": "localhost", "port": 5432}}
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result == config_data

    def test_load_yaml_config(self, tmp_path: Path):
        """Test loading a valid YAML configuration file."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_content = "database:\n  host: localhost\n  port: 5432\n"
        config_file.write_text(config_content)

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result == {"database": {"host": "localhost", "port": 5432}}

    def test_load_yml_config(self, tmp_path: Path):
        """Test loading a valid .yml configuration file."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yml"
        config_content = "app:\n  name: test\n"
        config_file.write_text(config_content)

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result == {"app": {"name": "test"}}

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        validator = ConfigValidator()

        with pytest.raises(FileNotFoundError):
            validator.load_config("/nonexistent/config.json")

    def test_invalid_json_syntax(self, tmp_path: Path):
        """Test that invalid JSON raises ConfigValidationError."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{invalid json}")

        validator = ConfigValidator()

        with pytest.raises(ConfigValidationError) as exc_info:
            validator.load_config(config_file)

        assert "Invalid JSON syntax" in str(exc_info.value)

    def test_invalid_yaml_syntax(self, tmp_path: Path):
        """Test that invalid YAML raises ConfigValidationError."""
        pytest.importorskip("yaml")

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        validator = ConfigValidator()

        with pytest.raises(ConfigValidationError) as exc_info:
            validator.load_config(config_file)

        assert "Invalid YAML syntax" in str(exc_info.value)

    def test_required_fields_present(self, tmp_path: Path):
        """Test validation passes when required fields are present."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"host": "localhost", "port": 5432}}
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator(
            required_fields=["database", "database.host", "database.port"]
        )
        result = validator.load_config(config_file)

        assert result == config_data

    def test_required_fields_missing(self, tmp_path: Path):
        """Test validation fails when required fields are missing."""
        config_file = tmp_path / "config.json"
        config_data = {"database": {"host": "localhost"}}
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator(
            required_fields=["database.port", "database.password"]
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            validator.load_config(config_file)

        assert "database.port" in str(exc_info.value)
        assert "database.password" in str(exc_info.value)

    def test_field_type_validation_pass(self, tmp_path: Path):
        """Test field type validation passes for correct types."""
        config_file = tmp_path / "config.json"
        config_data = {"port": 5432, "host": "localhost", "enabled": True}
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator(
            field_types={"port": int, "host": str, "enabled": bool}
        )
        result = validator.load_config(config_file)

        assert result == config_data

    def test_field_type_validation_fail(self, tmp_path: Path):
        """Test field type validation fails for wrong types."""
        config_file = tmp_path / "config.json"
        config_data = {"port": "5432", "enabled": "yes"}
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator(field_types={"port": int, "enabled": bool})

        with pytest.raises(ConfigValidationError) as exc_info:
            validator.load_config(config_file)

        assert "wrong type" in str(exc_info.value)

    def test_custom_validator_pass(self, tmp_path: Path):
        """Test custom validator that passes."""
        config_file = tmp_path / "config.json"
        config_data = {"port": 8080}
        config_file.write_text(json.dumps(config_data))

        def validate_port(value):
            return 1 <= value <= 65535

        validator = ConfigValidator(custom_validators={"port": validate_port})
        result = validator.load_config(config_file)

        assert result == config_data

    def test_custom_validator_fail(self, tmp_path: Path):
        """Test custom validator that fails."""
        config_file = tmp_path / "config.json"
        config_data = {"port": 99999}
        config_file.write_text(json.dumps(config_data))

        def validate_port(value):
            if not (1 <= value <= 65535):
                return "Port must be between 1 and 65535"
            return True

        validator = ConfigValidator(custom_validators={"port": validate_port})

        with pytest.raises(ConfigValidationError) as exc_info:
            validator.load_config(config_file)

        assert "Port must be between 1 and 65535" in str(exc_info.value)

    def test_env_var_substitution(self, tmp_path: Path):
        """Test environment variable substitution."""
        config_file = tmp_path / "config.json"
        config_content = '{"host": "${TEST_HOST}", "port": "${TEST_PORT}"}'
        config_file.write_text(config_content)

        with patch.dict(os.environ, {"TEST_HOST": "db.example.com", "TEST_PORT": "5432"}):
            validator = ConfigValidator()
            result = validator.load_config(config_file)

        assert result["host"] == "db.example.com"
        assert result["port"] == "5432"

    def test_env_var_with_default(self, tmp_path: Path):
        """Test environment variable substitution with default values."""
        config_file = tmp_path / "config.json"
        config_content = '{"host": "${UNDEFINED_HOST:localhost}", "port": "${UNDEFINED_PORT:5432}"}'
        config_file.write_text(config_content)

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result["host"] == "localhost"
        assert result["port"] == "5432"

    def test_env_var_override_default(self, tmp_path: Path):
        """Test that env var value overrides default."""
        config_file = tmp_path / "config.json"
        config_content = '{"host": "${TEST_HOST:localhost}"}'
        config_file.write_text(config_content)

        with patch.dict(os.environ, {"TEST_HOST": "production.example.com"}):
            validator = ConfigValidator()
            result = validator.load_config(config_file)

        assert result["host"] == "production.example.com"

    def test_env_var_substitution_disabled(self, tmp_path: Path):
        """Test disabling environment variable substitution."""
        config_file = tmp_path / "config.json"
        config_content = '{"host": "${TEST_HOST}"}'
        config_file.write_text(config_content)

        with patch.dict(os.environ, {"TEST_HOST": "db.example.com"}):
            validator = ConfigValidator()
            result = validator.load_config(config_file, substitute_env_vars=False)

        assert result["host"] == "${TEST_HOST}"

    def test_nested_field_access(self, tmp_path: Path):
        """Test accessing deeply nested fields."""
        config_file = tmp_path / "config.json"
        config_data = {
            "level1": {
                "level2": {
                    "level3": {"value": "deep"}
                }
            }
        }
        config_file.write_text(json.dumps(config_data))

        validator = ConfigValidator(
            required_fields=["level1.level2.level3.value"]
        )
        result = validator.load_config(config_file)

        assert result == config_data

    def test_empty_config_file(self, tmp_path: Path):
        """Test loading an empty configuration file."""
        config_file = tmp_path / "config.json"
        config_file.write_text("")

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result == {}

    def test_empty_json_object(self, tmp_path: Path):
        """Test loading a configuration file with empty object."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        validator = ConfigValidator()
        result = validator.load_config(config_file)

        assert result == {}


class TestConfigValidationError:
    """Tests for ConfigValidationError class."""

    def test_error_message_without_errors(self):
        """Test error message formatting without specific errors."""
        error = ConfigValidationError("Main error message")
        assert str(error) == "Main error message"

    def test_error_message_with_errors(self):
        """Test error message formatting with specific errors."""
        error = ConfigValidationError(
            "Validation failed",
            errors=["Error 1", "Error 2"]
        )
        message = str(error)
        assert "Validation failed" in message
        assert "Error 1" in message
        assert "Error 2" in message

    def test_errors_attribute(self):
        """Test that errors attribute is accessible."""
        errors = ["Error 1", "Error 2"]
        error = ConfigValidationError("Message", errors=errors)
        assert error.errors == errors


class TestValidateConfigOnStartup:
    """Tests for validate_config_on_startup convenience function."""

    def test_basic_usage(self, tmp_path: Path):
        """Test basic usage of validate_config_on_startup."""
        config_file = tmp_path / "config.json"
        config_data = {"app": {"name": "test"}}
        config_file.write_text(json.dumps(config_data))

        result = validate_config_on_startup(
            config_file,
            required_fields=["app.name"]
        )

        assert result == config_data

    def test_with_all_options(self, tmp_path: Path):
        """Test validate_config_on_startup with all options."""
        config_file = tmp_path / "config.json"
        config_data = {"port": 8080, "debug": True}
        config_file.write_text(json.dumps(config_data))

        def validate_port(value):
            return 1 <= value <= 65535

        result = validate_config_on_startup(
            config_file,
            required_fields=["port"],
            field_types={"port": int, "debug": bool},
            custom_validators={"port": validate_port}
        )

        assert result == config_data

    def test_validation_failure(self, tmp_path: Path):
        """Test validate_config_on_startup with validation failure."""
        config_file = tmp_path / "config.json"
        config_data = {"port": "invalid"}
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(ConfigValidationError):
            validate_config_on_startup(
                config_file,
                field_types={"port": int}
            )
