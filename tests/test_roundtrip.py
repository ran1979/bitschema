"""Round-trip correctness verification using property-based testing.

Tests the fundamental invariant: decode(encode(data)) == data
Uses Hypothesis to automatically generate edge cases and field combinations.
"""

import pytest
from hypothesis import given, strategies as st, settings

from bitschema import encode, decode, FieldLayout


class TestRoundTripSingleField:
    """Round-trip tests for individual field types."""

    @settings(max_examples=500)
    @given(st.booleans())
    def test_boolean_field_roundtrip(self, value):
        """Boolean field round-trips correctly for True/False."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            )
        ]

        original = {"flag": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=0, max_value=255))
    def test_unsigned_int_field_roundtrip(self, value):
        """Unsigned integer field round-trips correctly across full range."""
        layouts = [
            FieldLayout(
                name="count",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            )
        ]

        original = {"count": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=-128, max_value=127))
    def test_signed_int_field_roundtrip(self, value):
        """Signed integer field round-trips correctly with negative values."""
        layouts = [
            FieldLayout(
                name="temperature",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": -128, "max": 127},
                nullable=False,
            )
        ]

        original = {"temperature": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.sampled_from(["idle", "active", "error", "done"]))
    def test_enum_field_roundtrip(self, value):
        """Enum field round-trips correctly for all enum values."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=2,
                constraints={"values": ["idle", "active", "error", "done"]},
                nullable=False,
            )
        ]

        original = {"status": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestRoundTripNullableFields:
    """Round-trip tests for nullable fields."""

    @settings(max_examples=500)
    @given(st.none() | st.booleans())
    def test_nullable_boolean_roundtrip(self, value):
        """Nullable boolean round-trips correctly for None, True, False."""
        layouts = [
            FieldLayout(
                name="optional_flag",
                type="boolean",
                offset=0,
                bits=2,  # 1 presence + 1 value
                constraints={},
                nullable=True,
            )
        ]

        original = {"optional_flag": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.none() | st.integers(min_value=0, max_value=100))
    def test_nullable_int_roundtrip(self, value):
        """Nullable integer round-trips correctly for None and values."""
        layouts = [
            FieldLayout(
                name="optional_score",
                type="integer",
                offset=0,
                bits=8,  # 1 presence + 7 value
                constraints={"min": 0, "max": 100},
                nullable=True,
            )
        ]

        original = {"optional_score": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.none() | st.sampled_from(["red", "green", "blue"]))
    def test_nullable_enum_roundtrip(self, value):
        """Nullable enum round-trips correctly for None and enum values."""
        layouts = [
            FieldLayout(
                name="optional_color",
                type="enum",
                offset=0,
                bits=3,  # 1 presence + 2 value
                constraints={"values": ["red", "green", "blue"]},
                nullable=True,
            )
        ]

        original = {"optional_color": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestRoundTripMultipleFields:
    """Round-trip tests for schemas with multiple fields."""

    @settings(max_examples=500)
    @given(
        st.booleans(),
        st.integers(min_value=0, max_value=127),
        st.sampled_from(["low", "medium", "high"]),
    )
    def test_three_field_schema_roundtrip(self, active, count, priority):
        """Multi-field schema round-trips correctly."""
        layouts = [
            FieldLayout(
                name="active",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="count",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 127},
                nullable=False,
            ),
            FieldLayout(
                name="priority",
                type="enum",
                offset=8,
                bits=2,
                constraints={"values": ["low", "medium", "high"]},
                nullable=False,
            ),
        ]

        original = {"active": active, "count": count, "priority": priority}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(
        st.booleans(),
        st.none() | st.integers(min_value=-50, max_value=50),
        st.sampled_from(["new", "pending", "done"]),
    )
    def test_mixed_nullable_fields_roundtrip(self, flag, optional_value, status):
        """Schema with nullable and non-nullable fields round-trips correctly."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="optional_value",
                type="integer",
                offset=1,
                bits=8,  # 1 presence + 7 value
                constraints={"min": -50, "max": 50},
                nullable=True,
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["new", "pending", "done"]},
                nullable=False,
            ),
        ]

        original = {"flag": flag, "optional_value": optional_value, "status": status}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestRoundTripEdgeCases:
    """Round-trip tests for edge cases and boundaries."""

    @settings(max_examples=500)
    @given(
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
    )
    def test_adjacent_fields_no_overlap(self, value1, value2):
        """Adjacent fields don't interfere with each other."""
        layouts = [
            FieldLayout(
                name="field1",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
            FieldLayout(
                name="field2",
                type="integer",
                offset=8,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
        ]

        original = {"field1": value1, "field2": value2}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    def test_single_value_enum_roundtrip(self):
        """Single-value enum (0 bits) round-trips correctly."""
        layouts = [
            FieldLayout(
                name="constant",
                type="enum",
                offset=0,
                bits=0,  # Single value requires 0 bits
                constraints={"values": ["only"]},
                nullable=False,
            ),
            FieldLayout(
                name="counter",
                type="integer",
                offset=0,  # Starts at same offset since constant uses 0 bits
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
        ]

        original = {"constant": "only", "counter": 42}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=-1000, max_value=1000))
    def test_negative_range_roundtrip(self, value):
        """Negative integer ranges round-trip correctly."""
        layouts = [
            FieldLayout(
                name="offset",
                type="integer",
                offset=0,
                bits=11,  # (1000 - (-1000)).bit_length() = 11
                constraints={"min": -1000, "max": 1000},
                nullable=False,
            )
        ]

        original = {"offset": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    def test_all_fields_at_max_value(self):
        """All fields at maximum value pack and unpack correctly."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="max_int",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
            FieldLayout(
                name="last_enum",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            ),
        ]

        original = {"flag": True, "max_int": 255, "last_enum": "d"}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    def test_all_fields_at_min_value(self):
        """All fields at minimum value pack and unpack correctly."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="min_int",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": -128, "max": 127},
                nullable=False,
            ),
            FieldLayout(
                name="first_enum",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            ),
        ]

        original = {"flag": False, "min_int": -128, "first_enum": "a"}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestMultiFieldEdgeCases:
    """Edge case combinations for multi-field schemas."""

    @settings(max_examples=500)
    @given(
        st.booleans(),
        st.integers(min_value=0, max_value=255),
        st.sampled_from(["a", "b", "c", "d"]),
    )
    def test_all_fields_at_min_values(self, flag, int_val, enum_val):
        """All fields at minimum values encode/decode correctly."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="int_field",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
            FieldLayout(
                name="enum_field",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            ),
        ]

        # Test with minimum values
        original_min = {"flag": False, "int_field": 0, "enum_field": "a"}
        encoded = encode(original_min, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_min

        # Test with random values
        original_random = {"flag": flag, "int_field": int_val, "enum_field": enum_val}
        encoded = encode(original_random, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_random

    @settings(max_examples=500)
    @given(
        st.booleans(),
        st.integers(min_value=0, max_value=255),
        st.sampled_from(["a", "b", "c", "d"]),
    )
    def test_all_fields_at_max_values(self, flag, int_val, enum_val):
        """All fields at maximum values encode/decode correctly."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="int_field",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
            FieldLayout(
                name="enum_field",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            ),
        ]

        # Test with maximum values
        original_max = {"flag": True, "int_field": 255, "enum_field": "d"}
        encoded = encode(original_max, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_max

        # Test with random values
        original_random = {"flag": flag, "int_field": int_val, "enum_field": enum_val}
        encoded = encode(original_random, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_random

    @settings(max_examples=500)
    @given(
        st.integers(min_value=-100, max_value=100),
        st.integers(min_value=0, max_value=255),
    )
    def test_alternating_min_max_values(self, field1_val, field2_val):
        """Alternating min/max values across fields."""
        layouts = [
            FieldLayout(
                name="field1",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": -100, "max": 100},
                nullable=False,
            ),
            FieldLayout(
                name="field2",
                type="integer",
                offset=8,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
        ]

        # Test min-max pattern
        original_min_max = {"field1": -100, "field2": 255}
        encoded = encode(original_min_max, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_min_max

        # Test max-min pattern
        original_max_min = {"field1": 100, "field2": 0}
        encoded = encode(original_max_min, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_max_min

        # Test random values
        original_random = {"field1": field1_val, "field2": field2_val}
        encoded = encode(original_random, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original_random


class TestNullableStressTests:
    """Stress tests for nullable field patterns."""

    @settings(max_examples=500)
    @given(st.booleans())
    def test_all_nullable_fields_none(self, flag):
        """All nullable fields set to None simultaneously."""
        layouts = [
            FieldLayout(
                name="flag",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="opt1",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="opt2",
                type="enum",
                offset=9,
                bits=3,
                constraints={"values": ["a", "b", "c"]},
                nullable=True,
            ),
            FieldLayout(
                name="opt3",
                type="boolean",
                offset=12,
                bits=2,
                constraints={},
                nullable=True,
            ),
        ]

        original = {"flag": flag, "opt1": None, "opt2": None, "opt3": None}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original

    @settings(max_examples=500)
    @given(
        st.integers(min_value=0, max_value=100),
        st.sampled_from(["a", "b", "c"]),
        st.booleans(),
    )
    def test_all_nullable_fields_present(self, int_val, enum_val, bool_val):
        """All nullable fields with present values."""
        layouts = [
            FieldLayout(
                name="opt1",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="opt2",
                type="enum",
                offset=8,
                bits=3,
                constraints={"values": ["a", "b", "c"]},
                nullable=True,
            ),
            FieldLayout(
                name="opt3",
                type="boolean",
                offset=11,
                bits=2,
                constraints={},
                nullable=True,
            ),
        ]

        original = {"opt1": int_val, "opt2": enum_val, "opt3": bool_val}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original

    @settings(max_examples=500)
    @given(
        st.none() | st.integers(min_value=0, max_value=100),
        st.none() | st.sampled_from(["a", "b", "c"]),
        st.none() | st.booleans(),
    )
    def test_random_nullable_patterns(self, opt1, opt2, opt3):
        """Random patterns of None/present across nullable fields."""
        layouts = [
            FieldLayout(
                name="opt1",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="opt2",
                type="enum",
                offset=8,
                bits=3,
                constraints={"values": ["a", "b", "c"]},
                nullable=True,
            ),
            FieldLayout(
                name="opt3",
                type="boolean",
                offset=11,
                bits=2,
                constraints={},
                nullable=True,
            ),
        ]

        original = {"opt1": opt1, "opt2": opt2, "opt3": opt3}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)
        assert decoded == original


class TestRoundTripIntegration:
    """Integration test with full pipeline from schema file."""

    def test_full_pipeline_roundtrip(self, tmp_path):
        """Full pipeline from schema file to encode/decode round-trip."""
        from bitschema import parse_schema_file, compute_bit_layout
        from bitschema import BoolFieldDefinition, IntFieldDefinition, EnumFieldDefinition

        # Create test schema file
        schema_file = tmp_path / "test_schema.json"
        schema_file.write_text(
            """{
            "version": "1",
            "name": "TestSchema",
            "fields": {
                "active": {
                    "type": "bool"
                },
                "age": {
                    "type": "int",
                    "bits": 8,
                    "signed": false,
                    "min": 0,
                    "max": 150
                },
                "status": {
                    "type": "enum",
                    "values": ["new", "active", "archived"]
                },
                "score": {
                    "type": "int",
                    "bits": 7,
                    "signed": false,
                    "min": 0,
                    "max": 100,
                    "nullable": true
                }
            }
        }"""
        )

        # Load schema
        schema = parse_schema_file(schema_file)

        # Convert schema.fields dict to list format for compute_bit_layout
        fields_list = []
        for name, field_def in schema.fields.items():
            field_dict = {"name": name}
            if isinstance(field_def, BoolFieldDefinition):
                field_dict["type"] = "boolean"
                field_dict["nullable"] = field_def.nullable
            elif isinstance(field_def, IntFieldDefinition):
                field_dict.update({
                    "type": "integer",
                    "min": field_def.min,
                    "max": field_def.max,
                    "nullable": field_def.nullable,
                })
            elif isinstance(field_def, EnumFieldDefinition):
                field_dict.update({
                    "type": "enum",
                    "values": field_def.values,
                    "nullable": field_def.nullable,
                })
            fields_list.append(field_dict)

        # Compute layout
        layouts, total_bits = compute_bit_layout(fields_list)

        # Verify total bits
        assert total_bits == 1 + 8 + 2 + 8  # bool(1) + int(8) + enum(2) + nullable_int(1+7)

        # Test data variations
        test_cases = [
            {"active": True, "age": 42, "status": "active", "score": 85},
            {"active": False, "age": 0, "status": "new", "score": None},
            {"active": True, "age": 150, "status": "archived", "score": 0},
            {"active": False, "age": 75, "status": "active", "score": 100},
        ]

        for original in test_cases:
            encoded = encode(original, layouts)
            decoded = decode(encoded, layouts)
            assert decoded == original, f"Round-trip failed for {original}"
