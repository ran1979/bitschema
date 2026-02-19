"""Integration tests for complete BitSchema pipeline.

Tests end-to-end workflow:
1. Load schema file (JSON or YAML)
2. Parse to BitSchema model
3. Compute bit layout
4. Generate output schema
5. Encode and decode data
"""

import json
import pytest
from pathlib import Path

from bitschema import BitSchema, encode, decode
from bitschema.parser import parse_schema_file
from bitschema.layout import compute_bit_layout
from bitschema.output import generate_output_schema
from bitschema.models import IntFieldDefinition, BoolFieldDefinition, EnumFieldDefinition, BitmaskFieldDefinition


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


def test_e2e_user_profile_schema_encode_decode():
    """
    Complete E2E test: Schema definition → Layout → Encode → Decode

    Demonstrates realistic user profile with:
    - Integer field (age)
    - Enum field (subscription tier)
    - Boolean flags (active, verified)
    - Bitmask field (permissions)
    """
    # Step 1: Define schema programmatically
    schema = BitSchema(
        version="1",
        name="UserProfile",
        fields={
            "age": IntFieldDefinition(type="int", bits=7, min=0, max=120),
            "tier": EnumFieldDefinition(
                type="enum",
                values=["free", "basic", "premium", "enterprise"]
            ),
            "active": BoolFieldDefinition(type="bool"),
            "verified": BoolFieldDefinition(type="bool"),
            "permissions": BitmaskFieldDefinition(
                type="bitmask",
                flags={
                    "can_read": 0,
                    "can_write": 1,
                    "can_delete": 2,
                    "can_admin": 3,
                }
            ),
        }
    )

    # Step 2: Convert to layout format and compute bit layout
    fields_dict = [
        {"name": "age", "type": "integer", "min": 0, "max": 120},
        {"name": "tier", "type": "enum", "values": ["free", "basic", "premium", "enterprise"]},
        {"name": "active", "type": "boolean"},
        {"name": "verified", "type": "boolean"},
        {
            "name": "permissions",
            "type": "bitmask",
            "flags": {
                "can_read": 0,
                "can_write": 1,
                "can_delete": 2,
                "can_admin": 3,
            }
        },
    ]

    layouts, total_bits = compute_bit_layout(fields_dict)

    # Verify layout is valid
    assert total_bits > 0
    assert total_bits <= 64  # Must fit in 64-bit integer
    assert len(layouts) == 5  # All 5 fields have layouts

    # Step 3: Generate output schema
    output = generate_output_schema(schema, layouts, total_bits)
    assert output["version"] == "1"
    assert output["total_bits"] == total_bits
    assert len(output["fields"]) == 5

    # Step 4: Encode user data
    user_data = {
        "age": 25,
        "tier": "premium",  # Index 2 in enum
        "active": True,
        "verified": True,
        "permissions": {
            "can_read": True,
            "can_write": True,
            "can_delete": False,
            "can_admin": False,
        }
    }

    encoded = encode(user_data, layouts)
    assert isinstance(encoded, int)
    assert encoded >= 0
    assert encoded < 2**64  # Fits in 64-bit integer

    # Step 5: Decode back to original data
    decoded = decode(encoded, layouts)
    assert decoded == user_data

    # Step 6: Test different user profiles (round-trip verification)
    test_cases = [
        # Young free user, no permissions
        {
            "age": 18,
            "tier": "free",
            "active": True,
            "verified": False,
            "permissions": {"can_read": True, "can_write": False, "can_delete": False, "can_admin": False}
        },
        # Enterprise admin user
        {
            "age": 45,
            "tier": "enterprise",
            "active": True,
            "verified": True,
            "permissions": {"can_read": True, "can_write": True, "can_delete": True, "can_admin": True}
        },
        # Inactive basic user
        {
            "age": 32,
            "tier": "basic",
            "active": False,
            "verified": True,
            "permissions": {"can_read": True, "can_write": True, "can_delete": False, "can_admin": False}
        },
        # Edge case: max age
        {
            "age": 120,
            "tier": "premium",
            "active": True,
            "verified": True,
            "permissions": {"can_read": True, "can_write": False, "can_delete": False, "can_admin": False}
        },
    ]

    for test_user in test_cases:
        encoded_test = encode(test_user, layouts)
        decoded_test = decode(encoded_test, layouts)
        assert decoded_test == test_user, f"Round-trip failed for {test_user}"

    # Step 7: Verify each encoded value is unique
    encoded_values = [encode(user, layouts) for user in test_cases]
    assert len(encoded_values) == len(set(encoded_values)), "Different users should encode to different integers"
