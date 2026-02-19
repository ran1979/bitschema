"""Tests for JSON Schema Draft 2020-12 export functionality."""

import pytest
from bitschema.models import (
    BitSchema,
    BoolFieldDefinition,
    IntFieldDefinition,
    EnumFieldDefinition,
)
from bitschema.layout import compute_bit_layout
from bitschema.jsonschema import generate_json_schema


class TestBooleanFieldMapping:
    """Test boolean field mapping to JSON Schema."""

    def test_non_nullable_boolean(self):
        """Boolean field maps to {"type": "boolean"}."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={"active": BoolFieldDefinition(type="bool", nullable=False)},
        )
        layouts, _ = compute_bit_layout([{"name": "active", "type": "boolean"}])

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["active"] == {"type": "boolean"}
        assert "active" in result["required"]

    def test_nullable_boolean(self):
        """Nullable boolean maps to {"type": ["boolean", "null"]}."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={"active": BoolFieldDefinition(type="bool", nullable=True)},
        )
        layouts, _ = compute_bit_layout(
            [{"name": "active", "type": "boolean", "nullable": True}]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["active"] == {"type": ["boolean", "null"]}
        assert "active" not in result["required"]


class TestIntegerFieldMapping:
    """Test integer field mapping to JSON Schema."""

    def test_integer_with_constraints(self):
        """Integer field includes minimum and maximum constraints."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, min=0, max=100
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "age", "type": "integer", "min": 0, "max": 100}]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["age"] == {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        }
        assert "age" in result["required"]

    def test_nullable_integer_with_constraints(self):
        """Nullable integer uses type array and includes constraints."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "score": IntFieldDefinition(
                    type="int", bits=8, signed=False, nullable=True, min=0, max=255
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "score", "type": "integer", "min": 0, "max": 255, "nullable": True}]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["score"] == {
            "type": ["integer", "null"],
            "minimum": 0,
            "maximum": 255,
        }
        assert "score" not in result["required"]

    def test_signed_integer(self):
        """Signed integer includes negative minimum."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "temperature": IntFieldDefinition(
                    type="int", bits=8, signed=True, min=-50, max=50
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "temperature", "type": "integer", "min": -50, "max": 50}]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["temperature"] == {
            "type": "integer",
            "minimum": -50,
            "maximum": 50,
        }


class TestEnumFieldMapping:
    """Test enum field mapping to JSON Schema."""

    def test_enum_field(self):
        """Enum field maps to {"type": "string", "enum": [values]}."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "color": EnumFieldDefinition(
                    type="enum", values=["red", "green", "blue"], nullable=False
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "color", "type": "enum", "values": ["red", "green", "blue"]}]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["color"] == {
            "type": "string",
            "enum": ["red", "green", "blue"],
        }
        assert "color" in result["required"]

    def test_nullable_enum(self):
        """Nullable enum uses type array."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "status": EnumFieldDefinition(
                    type="enum", values=["pending", "active", "done"], nullable=True
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [
                {
                    "name": "status",
                    "type": "enum",
                    "values": ["pending", "active", "done"],
                    "nullable": True,
                }
            ]
        )

        result = generate_json_schema(schema, layouts)

        assert result["properties"]["status"] == {
            "type": ["string", "null"],
            "enum": ["pending", "active", "done"],
        }
        assert "status" not in result["required"]


class TestRequiredArray:
    """Test required array generation."""

    def test_required_includes_non_nullable(self):
        """Required array contains all non-nullable field names."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=False),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, nullable=True, min=0, max=100
                ),
                "name": EnumFieldDefinition(
                    type="enum", values=["alice", "bob"], nullable=False
                ),
            },
        )
        layouts, _ = compute_bit_layout(
            [
                {"name": "active", "type": "boolean"},
                {"name": "age", "type": "integer", "min": 0, "max": 100, "nullable": True},
                {"name": "name", "type": "enum", "values": ["alice", "bob"]},
            ]
        )

        result = generate_json_schema(schema, layouts)

        assert set(result["required"]) == {"active", "name"}
        assert "age" not in result["required"]

    def test_all_nullable_no_required(self):
        """Schema with all nullable fields has empty required array."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=True),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, nullable=True, min=0, max=100
                ),
            },
        )
        layouts, _ = compute_bit_layout(
            [
                {"name": "active", "type": "boolean", "nullable": True},
                {"name": "age", "type": "integer", "min": 0, "max": 100, "nullable": True},
            ]
        )

        result = generate_json_schema(schema, layouts)

        assert result["required"] == []


class TestSchemaMandatoryFields:
    """Test JSON Schema mandatory fields."""

    def test_includes_mandatory_fields(self):
        """Generated schema includes all mandatory Draft 2020-12 fields."""
        schema = BitSchema(
            version="1",
            name="UserProfile",
            fields={"active": BoolFieldDefinition(type="bool", nullable=False)},
        )
        layouts, _ = compute_bit_layout([{"name": "active", "type": "boolean"}])

        result = generate_json_schema(schema, layouts)

        # Mandatory fields
        assert result["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert result["type"] == "object"
        assert "properties" in result
        assert "required" in result

    def test_includes_title_and_id(self):
        """Schema includes title and $id fields."""
        schema = BitSchema(
            version="1",
            name="UserProfile",
            fields={"active": BoolFieldDefinition(type="bool", nullable=False)},
        )
        layouts, _ = compute_bit_layout([{"name": "active", "type": "boolean"}])

        result = generate_json_schema(schema, layouts)

        assert result["title"] == "UserProfile"
        assert "$id" in result
        assert "UserProfile" in result["$id"]

    def test_additional_properties_false(self):
        """Schema sets additionalProperties to false."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={"active": BoolFieldDefinition(type="bool", nullable=False)},
        )
        layouts, _ = compute_bit_layout([{"name": "active", "type": "boolean"}])

        result = generate_json_schema(schema, layouts)

        assert result["additionalProperties"] is False


class TestMetadataFields:
    """Test BitSchema-specific metadata fields."""

    def test_includes_bitschema_metadata(self):
        """Schema includes x-bitschema-* metadata fields."""
        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=False),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, min=0, max=100
                ),
            },
        )
        layouts, total_bits = compute_bit_layout(
            [
                {"name": "active", "type": "boolean"},
                {"name": "age", "type": "integer", "min": 0, "max": 100},
            ]
        )

        result = generate_json_schema(schema, layouts)

        assert result["x-bitschema-version"] == "1"
        assert result["x-bitschema-total-bits"] == total_bits


class TestSchemaValidation:
    """Test that generated schemas validate against JSON Schema spec."""

    def test_validates_against_draft_2020_12(self):
        """Generated schema validates against Draft 2020-12 meta-schema."""
        try:
            import jsonschema
            from jsonschema import Draft202012Validator
        except ImportError:
            pytest.skip("jsonschema library not installed")

        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=False),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, min=0, max=100
                ),
                "status": EnumFieldDefinition(
                    type="enum", values=["pending", "done"], nullable=True
                ),
            },
        )
        layouts, _ = compute_bit_layout(
            [
                {"name": "active", "type": "boolean"},
                {"name": "age", "type": "integer", "min": 0, "max": 100},
                {
                    "name": "status",
                    "type": "enum",
                    "values": ["pending", "done"],
                    "nullable": True,
                },
            ]
        )

        result = generate_json_schema(schema, layouts)

        # Validate against meta-schema
        Draft202012Validator.check_schema(result)

    def test_validates_sample_data(self):
        """Generated schema can validate sample data."""
        try:
            import jsonschema
            from jsonschema import validate
        except ImportError:
            pytest.skip("jsonschema library not installed")

        schema = BitSchema(
            version="1",
            name="TestSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=False),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, min=0, max=100
                ),
            },
        )
        layouts, _ = compute_bit_layout(
            [
                {"name": "active", "type": "boolean"},
                {"name": "age", "type": "integer", "min": 0, "max": 100},
            ]
        )

        json_schema = generate_json_schema(schema, layouts)

        # Valid data should pass
        valid_data = {"active": True, "age": 25}
        validate(instance=valid_data, schema=json_schema)

        # Invalid data should fail
        invalid_data = {"active": True, "age": 200}  # age exceeds maximum
        with pytest.raises(jsonschema.ValidationError):
            validate(instance=invalid_data, schema=json_schema)


class TestMultipleFields:
    """Test schemas with multiple fields of different types."""

    def test_mixed_field_types(self):
        """Schema with mixed field types maps correctly."""
        schema = BitSchema(
            version="1",
            name="ComplexSchema",
            fields={
                "active": BoolFieldDefinition(type="bool", nullable=False),
                "age": IntFieldDefinition(
                    type="int", bits=7, signed=False, min=0, max=100
                ),
                "status": EnumFieldDefinition(
                    type="enum", values=["pending", "active", "done"], nullable=True
                ),
            },
        )
        layouts, total_bits = compute_bit_layout(
            [
                {"name": "active", "type": "boolean"},
                {"name": "age", "type": "integer", "min": 0, "max": 100},
                {
                    "name": "status",
                    "type": "enum",
                    "values": ["pending", "active", "done"],
                    "nullable": True,
                },
            ]
        )

        result = generate_json_schema(schema, layouts)

        # Check all properties exist
        assert "active" in result["properties"]
        assert "age" in result["properties"]
        assert "status" in result["properties"]

        # Check types
        assert result["properties"]["active"]["type"] == "boolean"
        assert result["properties"]["age"]["type"] == "integer"
        assert result["properties"]["status"]["type"] == ["string", "null"]

        # Check required
        assert set(result["required"]) == {"active", "age"}

        # Check metadata
        assert result["x-bitschema-total-bits"] == total_bits
