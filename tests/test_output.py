"""Tests for output schema generation.

Tests cover OUTPUT-01, OUTPUT-02, OUTPUT-03 requirements:
- OUTPUT-01: JSON schema with version and total_bits
- OUTPUT-02: Per-field metadata (name, type, offset, bits, constraints)
- OUTPUT-03: JSON serializable output
"""

import json
import pytest

from bitschema.models import BitSchema, IntFieldDefinition, BoolFieldDefinition, EnumFieldDefinition
from bitschema.layout import compute_bit_layout, FieldLayout
from bitschema.output import generate_output_schema


def test_output_schema_structure():
    """Verify output schema has required keys: version, total_bits, fields."""
    # Create minimal schema
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "active": BoolFieldDefinition(type="bool"),
            "age": IntFieldDefinition(type="int", bits=7, min=0, max=100),
            "status": EnumFieldDefinition(type="enum", values=["new", "active"])
        }
    )

    # Compute layout
    # Convert Pydantic models to dict format expected by layout module
    fields_dict = []
    for name, field_def in schema.fields.items():
        field_dict = {"name": name}
        if isinstance(field_def, BoolFieldDefinition):
            field_dict["type"] = "boolean"
        elif isinstance(field_def, IntFieldDefinition):
            field_dict.update({
                "type": "integer",
                "min": field_def.min,
                "max": field_def.max
            })
        elif isinstance(field_def, EnumFieldDefinition):
            field_dict.update({
                "type": "enum",
                "values": field_def.values
            })
        fields_dict.append(field_dict)

    layouts, total_bits = compute_bit_layout(fields_dict)

    # Generate output
    output = generate_output_schema(schema, layouts, total_bits)

    # Verify structure
    assert "version" in output, "Output must include 'version'"
    assert "total_bits" in output, "Output must include 'total_bits'"
    assert "fields" in output, "Output must include 'fields'"

    # Verify values
    assert output["version"] == "1"
    assert output["total_bits"] == total_bits
    assert isinstance(output["fields"], list)
    assert len(output["fields"]) == 3


def test_output_field_metadata():
    """Verify each field has: name, type, offset, bits, constraints."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "active": BoolFieldDefinition(type="bool"),
        }
    )

    fields_dict = [{"name": "active", "type": "boolean"}]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    field = output["fields"][0]
    assert "name" in field, "Field must include 'name'"
    assert "type" in field, "Field must include 'type'"
    assert "offset" in field, "Field must include 'offset'"
    assert "bits" in field, "Field must include 'bits'"
    assert "constraints" in field, "Field must include 'constraints'"


def test_output_boolean_constraints():
    """Boolean field should have empty constraints dict."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "active": BoolFieldDefinition(type="bool"),
        }
    )

    fields_dict = [{"name": "active", "type": "boolean"}]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    field = output["fields"][0]
    assert field["name"] == "active"
    assert field["type"] == "boolean"
    assert field["constraints"] == {}


def test_output_integer_constraints():
    """Integer field should have min/max constraints."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "age": IntFieldDefinition(type="int", bits=7, min=0, max=100),
        }
    )

    fields_dict = [{"name": "age", "type": "integer", "min": 0, "max": 100}]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    field = output["fields"][0]
    assert field["name"] == "age"
    assert field["type"] == "integer"
    assert field["constraints"] == {"min": 0, "max": 100}


def test_output_enum_constraints():
    """Enum field should have values list in constraints."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "status": EnumFieldDefinition(type="enum", values=["new", "active", "archived"]),
        }
    )

    fields_dict = [{"name": "status", "type": "enum", "values": ["new", "active", "archived"]}]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    field = output["fields"][0]
    assert field["name"] == "status"
    assert field["type"] == "enum"
    assert field["constraints"] == {"values": ["new", "active", "archived"]}


def test_output_json_serializable():
    """Output should be JSON-serializable (no custom types)."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "active": BoolFieldDefinition(type="bool"),
            "age": IntFieldDefinition(type="int", bits=7, min=0, max=100),
            "status": EnumFieldDefinition(type="enum", values=["new", "active"]),
        }
    )

    fields_dict = [
        {"name": "active", "type": "boolean"},
        {"name": "age", "type": "integer", "min": 0, "max": 100},
        {"name": "status", "type": "enum", "values": ["new", "active"]},
    ]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    # Should serialize without errors
    serialized = json.dumps(output)
    assert isinstance(serialized, str)

    # Should deserialize back to same structure
    deserialized = json.loads(serialized)
    assert deserialized == output


def test_output_offset_and_bits_match_layout():
    """Output offset and bits should match computed layout."""
    schema = BitSchema(
        version="1",
        name="TestSchema",
        fields={
            "active": BoolFieldDefinition(type="bool"),
            "age": IntFieldDefinition(type="int", bits=7, min=0, max=100),
        }
    )

    fields_dict = [
        {"name": "active", "type": "boolean"},
        {"name": "age", "type": "integer", "min": 0, "max": 100},
    ]
    layouts, total_bits = compute_bit_layout(fields_dict)

    output = generate_output_schema(schema, layouts, total_bits)

    # First field (active) at offset 0, 1 bit
    assert output["fields"][0]["offset"] == 0
    assert output["fields"][0]["bits"] == 1

    # Second field (age) at offset 1, 7 bits
    assert output["fields"][1]["offset"] == 1
    assert output["fields"][1]["bits"] == 7
