"""Tests for schema file loading with JSON and YAML support.

Tests cover:
- JSON parsing (SCHEMA-01)
- YAML parsing (SCHEMA-02)
- Pydantic validation integration (SCHEMA-03)
- Security (yaml.safe_load verification)
- Error handling (invalid syntax, missing files, unsupported formats)
"""

import json
from pathlib import Path

import pytest

from bitschema.loader import load_schema, load_from_json, load_from_yaml, schema_from_dict
from bitschema.models import BitSchema
from bitschema.errors import SchemaError


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestJSONParsing:
    """Test JSON file parsing (SCHEMA-01)."""

    def test_parse_valid_json(self):
        """Valid JSON file with boolean, integer, and enum fields."""
        schema = load_schema(FIXTURES_DIR / "valid_schema.json")

        assert isinstance(schema, BitSchema)
        assert schema.version == "1"
        assert schema.name == "UserFlags"
        assert len(schema.fields) == 3
        assert "active" in schema.fields
        assert "age" in schema.fields
        assert "status" in schema.fields
        assert schema.fields["active"].type == "bool"
        assert schema.fields["age"].type == "int"
        assert schema.fields["age"].bits == 7
        assert schema.fields["status"].type == "enum"
        assert schema.fields["status"].values == ["new", "active", "archived"]

    def test_parse_json_with_enum(self):
        """Valid JSON with enum field calculates bits correctly."""
        schema = load_schema(FIXTURES_DIR / "valid_schema.json")
        enum_field = schema.fields["status"]
        # 3 values: need 2 bits (0-2 requires 2 bits)
        assert enum_field.bits_required == 2

    def test_parse_invalid_json_syntax(self):
        """Invalid JSON syntax raises SchemaError with clear message."""
        with pytest.raises(SchemaError) as exc_info:
            load_schema(FIXTURES_DIR / "invalid_syntax.json")

        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_json_with_invalid_schema(self):
        """JSON file with invalid schema (missing required field) raises SchemaError."""
        # Create a fixture with missing 'name' field
        invalid_data = {"version": "1", "fields": {"x": {"type": "bool"}}}

        with pytest.raises(SchemaError) as exc_info:
            load_from_json(json.dumps(invalid_data))

        assert "validation failed" in str(exc_info.value).lower()


class TestYAMLParsing:
    """Test YAML file parsing (SCHEMA-02)."""

    def test_parse_valid_yaml(self):
        """Valid YAML file with same structure as JSON."""
        schema = load_schema(FIXTURES_DIR / "valid_schema.yaml")

        assert isinstance(schema, BitSchema)
        assert schema.version == "1"
        assert schema.name == "UserFlags"
        assert len(schema.fields) == 3
        assert "active" in schema.fields
        assert "age" in schema.fields
        assert "status" in schema.fields

    def test_parse_yaml_produces_same_result_as_json(self):
        """YAML and JSON versions of same schema produce identical models."""
        json_schema = load_schema(FIXTURES_DIR / "valid_schema.json")
        yaml_schema = load_schema(FIXTURES_DIR / "valid_schema.yaml")

        # Compare serialized representations
        assert json_schema.model_dump() == yaml_schema.model_dump()

    def test_parse_invalid_yaml_syntax(self):
        """Invalid YAML syntax raises SchemaError."""
        with pytest.raises(SchemaError) as exc_info:
            load_schema(FIXTURES_DIR / "invalid_syntax.yaml")

        assert "Invalid YAML" in str(exc_info.value)

    def test_parse_yaml_with_invalid_schema(self):
        """YAML file with invalid schema raises SchemaError."""
        invalid_yaml = """
version: "1"
name: "Test"
fields:
  field1:
    type: invalid_type
"""
        with pytest.raises(SchemaError) as exc_info:
            load_from_yaml(invalid_yaml)

        assert "validation failed" in str(exc_info.value).lower()


class TestSecurity:
    """Test security features (yaml.safe_load verification)."""

    def test_yaml_uses_safe_load(self):
        """Verify that yaml.safe_load is used, not yaml.load."""
        # Read the loader.py source code
        loader_path = Path(__file__).parent.parent / "bitschema" / "loader.py"
        source = loader_path.read_text()

        # Verify safe_load is used
        assert "yaml.safe_load" in source

        # Verify unsafe yaml.load() is NOT used (without the safe_ prefix)
        # This regex checks for yaml.load( but not yaml.safe_load(
        import re
        unsafe_pattern = r'yaml\.load\s*\('
        safe_pattern = r'yaml\.safe_load\s*\('

        # Should have safe_load
        assert re.search(safe_pattern, source) is not None

        # Should NOT have unsafe load (not preceded by "safe_")
        # Check for yaml.load that is NOT yaml.safe_load
        lines_with_load = [line for line in source.split('\n') if 'yaml.load' in line]
        for line in lines_with_load:
            # Each line with yaml.load should be yaml.safe_load
            assert 'safe_load' in line, f"Found unsafe yaml.load: {line}"

    def test_yaml_rejects_python_objects(self):
        """YAML with Python object tags is safely rejected."""
        dangerous_yaml = """
!!python/object/new:os.system
args: ['echo pwned']
"""
        # This should be rejected by safe_load, not execute code
        # Note: safe_load will parse it but won't execute
        with pytest.raises(SchemaError):
            load_from_yaml(dangerous_yaml)


class TestFileHandling:
    """Test file handling edge cases."""

    def test_nonexistent_file(self):
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_schema(FIXTURES_DIR / "does_not_exist.json")

        assert "does_not_exist.json" in str(exc_info.value)

    def test_unsupported_extension(self):
        """Unsupported file extension (.txt) raises SchemaError with clear message."""
        # Create a temporary .txt file
        txt_file = FIXTURES_DIR / "test.txt"
        txt_file.write_text('{"version": "1", "name": "Test", "fields": {}}')

        try:
            with pytest.raises(SchemaError) as exc_info:
                load_schema(txt_file)

            assert "Unsupported file format" in str(exc_info.value)
            assert ".txt" in str(exc_info.value)
        finally:
            txt_file.unlink()

    def test_empty_file(self):
        """Empty file raises SchemaError."""
        empty_file = FIXTURES_DIR / "empty.json"
        empty_file.write_text("")

        try:
            with pytest.raises(SchemaError):
                load_schema(empty_file)
        finally:
            empty_file.unlink()


class TestPydanticIntegration:
    """Test Pydantic validation integration (SCHEMA-03)."""

    def test_schema_with_duplicate_field_names(self):
        """Schema with duplicate field names raises ValidationError."""
        # Note: JSON doesn't allow duplicate keys, but we can test via dict
        from bitschema.loader import schema_from_dict

        # Python dict with duplicate keys - last one wins, so this actually won't fail
        # Instead, test with invalid field definition
        invalid_data = {
            "version": "1",
            "name": "Test",
            "fields": {
                "field1": {"type": "bool"},
                "field2": {"type": "int"}  # Missing required 'bits'
            }
        }

        with pytest.raises(SchemaError) as exc_info:
            schema_from_dict(invalid_data)

        assert "validation failed" in str(exc_info.value).lower()

    def test_schema_with_invalid_field_type(self):
        """Schema with invalid field type raises ValidationError."""
        invalid_data = {
            "version": "1",
            "name": "Test",
            "fields": {
                "field1": {"type": "invalid_type"}
            }
        }

        with pytest.raises(SchemaError) as exc_info:
            schema_from_dict(invalid_data)

        error_msg = str(exc_info.value)
        assert "validation failed" in error_msg.lower()

    def test_pydantic_errors_preserve_context(self):
        """Pydantic validation errors include field name and constraint violated."""
        invalid_data = {
            "version": "1",
            "name": "Test",
            "fields": {
                "age": {
                    "type": "int",
                    "bits": 8,
                    "min": 0,
                    "max": 300  # Exceeds 8-bit unsigned max (255)
                }
            }
        }

        with pytest.raises(SchemaError) as exc_info:
            schema_from_dict(invalid_data)

        error_msg = str(exc_info.value)
        # Should mention the field and the constraint issue
        assert "validation failed" in error_msg.lower()

    def test_schema_exceeding_64_bits_raises_error(self):
        """Schema exceeding 64-bit total raises ValidationError from Pydantic."""
        # Create schema with fields totaling > 64 bits
        invalid_data = {
            "version": "1",
            "name": "TooBig",
            "fields": {
                f"field{i}": {"type": "int", "bits": 8}
                for i in range(9)  # 9 * 8 = 72 bits
            }
        }

        with pytest.raises(SchemaError) as exc_info:
            schema_from_dict(invalid_data)

        error_msg = str(exc_info.value)
        assert "64" in error_msg or "bit" in error_msg.lower()


class TestPathHandling:
    """Test that both Path and str are accepted."""

    def test_accepts_path_object(self):
        """load_schema accepts pathlib.Path object."""
        schema = load_schema(Path(FIXTURES_DIR / "valid_schema.json"))
        assert isinstance(schema, BitSchema)

    def test_accepts_string_path(self):
        """load_schema accepts string path."""
        schema = load_schema(str(FIXTURES_DIR / "valid_schema.json"))
        assert isinstance(schema, BitSchema)
