"""Tests for parser.py module - wraps loader tests for parse_schema_file API.

This test file validates the parse_schema_file function which is an alias
for load_schema from the loader module. It ensures the parser API works
as specified in the plan while delegating to the existing loader implementation.
"""

from pathlib import Path
import pytest

from bitschema.parser import parse_schema_file
from bitschema.models import BitSchema
from bitschema.errors import SchemaError


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestParseSchemaFile:
    """Test parse_schema_file function (wraps load_schema)."""

    def test_parse_valid_json_file(self):
        """Parse valid JSON file returns BitSchema instance."""
        schema = parse_schema_file(FIXTURES_DIR / "valid_schema.json")

        assert isinstance(schema, BitSchema)
        assert schema.name == "UserFlags"
        assert len(schema.fields) == 3

    def test_parse_valid_yaml_file(self):
        """Parse valid YAML file returns BitSchema instance."""
        schema = parse_schema_file(FIXTURES_DIR / "valid_schema.yaml")

        assert isinstance(schema, BitSchema)
        assert schema.name == "UserFlags"
        assert len(schema.fields) == 3

    def test_parse_accepts_string_path(self):
        """parse_schema_file accepts string path."""
        schema = parse_schema_file(str(FIXTURES_DIR / "valid_schema.json"))
        assert isinstance(schema, BitSchema)

    def test_parse_accepts_path_object(self):
        """parse_schema_file accepts pathlib.Path object."""
        schema = parse_schema_file(Path(FIXTURES_DIR / "valid_schema.json"))
        assert isinstance(schema, BitSchema)

    def test_parse_invalid_json_syntax(self):
        """Invalid JSON syntax raises SchemaError."""
        with pytest.raises(SchemaError):
            parse_schema_file(FIXTURES_DIR / "invalid_syntax.json")

    def test_parse_invalid_yaml_syntax(self):
        """Invalid YAML syntax raises SchemaError."""
        with pytest.raises(SchemaError):
            parse_schema_file(FIXTURES_DIR / "invalid_syntax.yaml")

    def test_parse_nonexistent_file(self):
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_schema_file(FIXTURES_DIR / "does_not_exist.json")

    def test_parse_unsupported_extension(self):
        """Unsupported file extension raises SchemaError."""
        txt_file = FIXTURES_DIR / "test.txt"
        txt_file.write_text('{"version": "1", "name": "Test", "fields": {}}')

        try:
            with pytest.raises(SchemaError) as exc_info:
                parse_schema_file(txt_file)

            assert "Unsupported file format" in str(exc_info.value)
        finally:
            txt_file.unlink()


class TestSecurityVerification:
    """Verify security requirements are met."""

    def test_yaml_safe_load_is_used(self):
        """Verify yaml.safe_load is used in the underlying loader."""
        # Check the loader module that parser delegates to
        loader_path = Path(__file__).parent.parent / "bitschema" / "loader.py"
        source = loader_path.read_text()

        # Must use safe_load
        assert "yaml.safe_load" in source

        # Should not use unsafe yaml.load
        lines_with_load = [line for line in source.split('\n') if 'yaml.load' in line]
        for line in lines_with_load:
            assert 'safe_load' in line, f"Found unsafe yaml.load: {line}"
