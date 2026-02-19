"""Tests for bit layout computation."""

import pytest

from bitschema.errors import SchemaError
from bitschema.layout import FieldLayout, compute_bit_layout


# Mock field objects for testing without full Pydantic models
def make_boolean_field(name: str) -> dict:
    """Create mock boolean field."""
    return {"name": name, "type": "boolean"}


def make_integer_field(name: str, min_value: int, max_value: int) -> dict:
    """Create mock integer field."""
    return {"name": name, "type": "integer", "min": min_value, "max": max_value}


def make_enum_field(name: str, values: list[str]) -> dict:
    """Create mock enum field."""
    return {"name": name, "type": "enum", "values": values}


# Test bit width calculations (TYPE-04)


def test_bit_width_boolean():
    """Boolean fields require exactly 1 bit."""
    fields = [make_boolean_field("is_active")]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 1
    assert layouts[0].bits == 1
    assert total_bits == 1


def test_bit_width_integer_range():
    """Integer fields use minimum bits to represent range."""
    # 0..1 requires 1 bit
    fields = [make_integer_field("small", 0, 1)]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 1

    # 0..255 requires 8 bits
    fields = [make_integer_field("byte", 0, 255)]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 8

    # 0..256 requires 9 bits (257 values)
    fields = [make_integer_field("large", 0, 256)]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 9


def test_bit_width_signed_integer():
    """Signed integers compute bits based on range size."""
    # -128..127 has range 255, requires 8 bits
    fields = [make_integer_field("signed", -128, 127)]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 8

    # -1..1 has range 2, requires 2 bits (values: -1, 0, 1)
    fields = [make_integer_field("small_signed", -1, 1)]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 2


def test_bit_width_enum():
    """Enum fields use bits for index representation."""
    # 3 values (indices 0..2) require 2 bits
    fields = [make_enum_field("status", ["pending", "active", "done"])]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 2

    # 2 values (indices 0..1) require 1 bit
    fields = [make_enum_field("flag", ["on", "off"])]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 1

    # 4 values (indices 0..3) require 2 bits
    fields = [make_enum_field("direction", ["north", "south", "east", "west"])]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 2


def test_bit_width_single_value_enum():
    """Single-value enums require 0 bits (constant)."""
    # Single value has no variance, needs 0 bits
    fields = [make_enum_field("constant", ["only_value"])]
    layouts, total = compute_bit_layout(fields)
    assert layouts[0].bits == 0
    assert total == 0


# Test sequential offset assignment (LAYOUT-01, LAYOUT-02)


def test_sequential_offset_assignment():
    """Fields get sequential offsets starting from 0."""
    fields = [
        make_boolean_field("is_active"),  # 1 bit at offset 0
        make_integer_field("age", 0, 255),  # 8 bits at offset 1
    ]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 2
    assert layouts[0].offset == 0
    assert layouts[0].bits == 1
    assert layouts[1].offset == 1
    assert layouts[1].bits == 8
    assert total_bits == 9


def test_field_order_preserved():
    """Field order in schema determines bit offset order."""
    fields = [
        make_integer_field("first", 0, 15),  # 4 bits at offset 0
        make_boolean_field("second"),  # 1 bit at offset 4
        make_integer_field("third", 0, 3),  # 2 bits at offset 5
    ]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 3
    assert layouts[0].name == "first"
    assert layouts[0].offset == 0
    assert layouts[0].bits == 4

    assert layouts[1].name == "second"
    assert layouts[1].offset == 4
    assert layouts[1].bits == 1

    assert layouts[2].name == "third"
    assert layouts[2].offset == 5
    assert layouts[2].bits == 2

    assert total_bits == 7


# Test 64-bit limit validation (LAYOUT-05)


def test_64_bit_limit_exact():
    """Schema with exactly 64 bits succeeds."""
    # 8 fields of 8 bits each = 64 bits exactly
    fields = [make_integer_field(f"field{i}", 0, 255) for i in range(8)]
    layouts, total_bits = compute_bit_layout(fields)

    assert total_bits == 64
    assert len(layouts) == 8


def test_64_bit_limit_exceeded():
    """Schema exceeding 64 bits raises SchemaError."""
    # 9 fields of 8 bits each = 72 bits
    fields = [make_integer_field(f"field{i}", 0, 255) for i in range(9)]

    with pytest.raises(SchemaError) as exc_info:
        compute_bit_layout(fields)

    error = exc_info.value
    assert "exceeds 64-bit limit" in error.message.lower()
    assert "72 bits" in error.message


def test_64_bit_limit_breakdown_message():
    """SchemaError for overflow includes per-field breakdown."""
    fields = [
        make_integer_field("large1", 0, 255),  # 8 bits
        make_integer_field("large2", 0, 255),  # 8 bits
        make_integer_field("large3", 0, 255),  # 8 bits
        make_integer_field("large4", 0, 255),  # 8 bits
        make_integer_field("large5", 0, 255),  # 8 bits
        make_integer_field("large6", 0, 255),  # 8 bits
        make_integer_field("large7", 0, 255),  # 8 bits
        make_integer_field("large8", 0, 255),  # 8 bits
        make_boolean_field("overflow"),  # 1 bit -> total 65
    ]

    with pytest.raises(SchemaError) as exc_info:
        compute_bit_layout(fields)

    error = exc_info.value
    # Should include breakdown with field names and bit counts
    assert "large1=8" in error.message or "large1: 8" in error.message
    assert "overflow=1" in error.message or "overflow: 1" in error.message
    assert "65 bits" in error.message


# Test determinism (LAYOUT-01)


def test_layout_determinism():
    """Same schema computed twice produces identical offsets."""
    fields = [
        make_boolean_field("is_active"),
        make_integer_field("age", 0, 127),
        make_enum_field("status", ["pending", "active", "done"]),
    ]

    layouts1, total1 = compute_bit_layout(fields)
    layouts2, total2 = compute_bit_layout(fields)

    assert total1 == total2
    assert len(layouts1) == len(layouts2)

    for l1, l2 in zip(layouts1, layouts2):
        assert l1.name == l2.name
        assert l1.type == l2.type
        assert l1.offset == l2.offset
        assert l1.bits == l2.bits
        assert l1.constraints == l2.constraints


# Test FieldLayout structure


def test_field_layout_structure():
    """FieldLayout contains all required fields."""
    fields = [make_integer_field("test", 0, 100)]
    layouts, total = compute_bit_layout(fields)

    layout = layouts[0]
    assert hasattr(layout, "name")
    assert hasattr(layout, "type")
    assert hasattr(layout, "offset")
    assert hasattr(layout, "bits")
    assert hasattr(layout, "constraints")

    assert layout.name == "test"
    assert layout.type == "integer"
    assert layout.offset == 0
    assert layout.bits == 7  # 0..100 requires 7 bits (101 values)
    assert isinstance(layout.constraints, dict)


# Test nullable field presence bit tracking (TYPE-06)


def test_nullable_boolean_adds_presence_bit():
    """Nullable boolean field requires 2 bits (1 presence + 1 value)."""
    fields = [{"name": "flag", "type": "boolean", "nullable": True}]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 1
    assert layouts[0].bits == 2  # 1 for presence + 1 for value
    assert total_bits == 2


def test_non_nullable_boolean_no_presence_bit():
    """Non-nullable boolean field requires only 1 bit."""
    fields = [{"name": "flag", "type": "boolean", "nullable": False}]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 1
    assert layouts[0].bits == 1  # Only value bit, no presence bit
    assert total_bits == 1


def test_nullable_integer_adds_presence_bit():
    """Nullable integer field adds 1 bit for presence tracking."""
    # 0..127 requires 7 bits, + 1 presence bit = 8 total
    fields = [{"name": "age", "type": "integer", "min": 0, "max": 127, "nullable": True}]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 1
    assert layouts[0].bits == 8  # 7 for value + 1 for presence
    assert total_bits == 8


def test_nullable_enum_adds_presence_bit():
    """Nullable enum field adds 1 bit for presence tracking."""
    # 3 values require 2 bits, + 1 presence bit = 3 total
    fields = [{"name": "status", "type": "enum", "values": ["a", "b", "c"], "nullable": True}]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 1
    assert layouts[0].bits == 3  # 2 for enum + 1 for presence
    assert total_bits == 3


def test_mixed_nullable_and_non_nullable_fields():
    """Schema with mix of nullable and non-nullable fields calculates correctly."""
    fields = [
        {"name": "id", "type": "integer", "min": 0, "max": 255, "nullable": False},  # 8 bits
        {"name": "active", "type": "boolean", "nullable": True},  # 2 bits (1 + 1)
        {"name": "score", "type": "integer", "min": 0, "max": 100, "nullable": True},  # 8 bits (7 + 1)
    ]
    layouts, total_bits = compute_bit_layout(fields)

    assert len(layouts) == 3
    assert layouts[0].bits == 8  # id: 8 bits (no presence bit)
    assert layouts[1].bits == 2  # active: 1 value + 1 presence
    assert layouts[2].bits == 8  # score: 7 value + 1 presence
    assert total_bits == 18  # 8 + 2 + 8


def test_nullable_flag_in_field_layout():
    """FieldLayout should track nullable flag."""
    fields = [{"name": "value", "type": "boolean", "nullable": True}]
    layouts, _ = compute_bit_layout(fields)

    assert hasattr(layouts[0], "nullable")
    assert layouts[0].nullable is True


def test_64_bit_limit_includes_presence_bits():
    """64-bit limit validation should include presence bits."""
    # 8 fields of 8 bits each = 64 bits (no presence bits)
    fields = [
        {"name": f"field{i}", "type": "integer", "min": 0, "max": 255, "nullable": False}
        for i in range(8)
    ]
    layouts, total_bits = compute_bit_layout(fields)
    assert total_bits == 64  # Should succeed

    # Now add nullable to one field -> 65 bits total (should fail)
    fields[0]["nullable"] = True
    with pytest.raises(SchemaError) as exc_info:
        compute_bit_layout(fields)

    error = exc_info.value
    assert "exceeds 64-bit limit" in error.message.lower()
    assert "65 bits" in error.message
