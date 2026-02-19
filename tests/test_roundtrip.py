"""Round-trip correctness verification using property-based testing.

Tests the fundamental invariant: decode(encode(data)) == data
Uses Hypothesis to automatically generate edge cases and field combinations.
"""

import pytest
from hypothesis import given, strategies as st

from bitschema import encode, decode, FieldLayout


class TestRoundTripSingleField:
    """Round-trip tests for individual field types."""

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
