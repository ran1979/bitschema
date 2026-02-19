"""Integration tests for complete BitSchema pipeline.

Tests end-to-end workflow:
1. Load schema file (JSON or YAML)
2. Parse to BitSchema model
3. Compute bit layout
4. Generate output schema
"""

import json
import pytest
from pathlib import Path

from bitschema import BitSchema
from bitschema.parser import parse_schema_file
from bitschema.layout import compute_bit_layout
from bitschema.output import generate_output_schema
from bitschema.models import IntFieldDefinition, BoolFieldDefinition, EnumFieldDefinition


def test_json_file_to_output_schema():
    """Full pipeline: JSON file → parsed schema → layout → output."""
    # Use existing test fixture
    schema_path = Path("tests/fixtures/valid_schema.json")

    # Step 1: Parse schema file
    schema = parse_schema_file(schema_path)
    assert isinstance(schema, BitSchema)
    assert schema.name == "UserFlags"

    # Step 2: Convert to layout format and compute layout
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
    assert total_bits > 0

    # Step 3: Generate output schema
    output = generate_output_schema(schema, layouts, total_bits)

    # Verify output structure
    assert output["version"] == "1"
    assert output["total_bits"] == total_bits
    assert len(output["fields"]) == 3


def test_yaml_file_to_output_schema():
    """Full pipeline: YAML file → parsed schema → layout → output."""
    # Use existing YAML fixture (matches valid_schema.json)
    yaml_path = Path("tests/fixtures/valid_schema.yaml")

    # Step 1: Parse YAML schema file
    schema = parse_schema_file(yaml_path)
    assert isinstance(schema, BitSchema)
    assert schema.name == "UserFlags"

    # Step 2: Compute layout
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

    # Step 3: Generate output
    output = generate_output_schema(schema, layouts, total_bits)

    # Verify output matches JSON version
    assert output["version"] == "1"
    assert output["total_bits"] == total_bits
    assert len(output["fields"]) == 3


def test_pipeline_field_names_preserved():
    """Field names from input file should match output field names."""
    schema_path = Path("tests/fixtures/valid_schema.json")

    schema = parse_schema_file(schema_path)

    # Get input field names
    input_names = list(schema.fields.keys())

    # Compute layout
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
    output = generate_output_schema(schema, layouts, total_bits)

    # Get output field names
    output_names = [field["name"] for field in output["fields"]]

    # Verify all input names present in output
    assert input_names == output_names


def test_pipeline_total_bits_correct():
    """Computed total_bits should match output total_bits."""
    schema_path = Path("tests/fixtures/valid_schema.json")

    schema = parse_schema_file(schema_path)

    # Compute layout
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
    output = generate_output_schema(schema, layouts, total_bits)

    # Verify total_bits matches
    assert output["total_bits"] == total_bits

    # Verify total_bits equals sum of field bits
    sum_of_bits = sum(field["bits"] for field in output["fields"])
    assert output["total_bits"] == sum_of_bits


def test_public_api_imports():
    """Verify all components importable from bitschema package root."""
    # This test verifies __all__ exports
    try:
        from bitschema import (
            BitSchema,
            parse_schema_file,
            compute_bit_layout,
            generate_output_schema,
        )

        # Verify they're callable/usable
        assert BitSchema is not None
        assert callable(parse_schema_file)
        assert callable(compute_bit_layout)
        assert callable(generate_output_schema)

    except ImportError as e:
        pytest.fail(f"Public API import failed: {e}")


def test_64_bit_exact_boundary():
    """Schema with exactly 64 bits should succeed."""
    # Create schema with exactly 64 bits
    schema = BitSchema(
        version="1",
        name="MaxBits",
        fields={
            "field1": IntFieldDefinition(type="int", bits=32, min=0, max=2**32-1),
            "field2": IntFieldDefinition(type="int", bits=32, min=0, max=2**32-1),
        }
    )

    # Convert to layout format
    fields_dict = [
        {"name": "field1", "type": "integer", "min": 0, "max": 2**32-1},
        {"name": "field2", "type": "integer", "min": 0, "max": 2**32-1},
    ]

    # Should succeed
    layouts, total_bits = compute_bit_layout(fields_dict)
    assert total_bits == 64

    # Should generate output successfully
    output = generate_output_schema(schema, layouts, total_bits)
    assert output["total_bits"] == 64
