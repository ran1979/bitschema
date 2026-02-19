"""Systematic boundary condition testing using property-based tests.

Tests edge cases and boundary conditions for all field types to ensure
bit-packing correctness at min/max values, zero-bit fields, and nullable
combinations.
"""

import pytest
from hypothesis import given, strategies as st, settings

from bitschema import encode, decode, FieldLayout


class TestIntegerBoundaries:
    """Boundary condition tests for integer fields."""

    @settings(max_examples=500)
    @given(st.integers(min_value=0, max_value=255))
    def test_unsigned_byte_min_max(self, value):
        """Unsigned 8-bit integer at min/max boundaries."""
        layouts = [
            FieldLayout(
                name="byte_field",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            )
        ]

        original = {"byte_field": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=-128, max_value=127))
    def test_signed_byte_min_max(self, value):
        """Signed 8-bit integer at min/max boundaries."""
        layouts = [
            FieldLayout(
                name="signed_byte",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": -128, "max": 127},
                nullable=False,
            )
        ]

        original = {"signed_byte": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=-1000, max_value=1000))
    def test_negative_range_boundaries(self, value):
        """Negative ranges handle min/max correctly."""
        layouts = [
            FieldLayout(
                name="offset_value",
                type="integer",
                offset=0,
                bits=11,  # (1000 - (-1000)).bit_length()
                constraints={"min": -1000, "max": 1000},
                nullable=False,
            )
        ]

        original = {"offset_value": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=42, max_value=42))
    def test_single_value_range(self, value):
        """Single-value range (min == max) works correctly."""
        layouts = [
            FieldLayout(
                name="constant",
                type="integer",
                offset=0,
                bits=0,  # No bits needed for single value
                constraints={"min": 42, "max": 42},
                nullable=False,
            )
        ]

        original = {"constant": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=0, max_value=2**63 - 1))
    def test_maximum_64bit_field(self, value):
        """Maximum 64-bit field uses full range."""
        layouts = [
            FieldLayout(
                name="max_field",
                type="integer",
                offset=0,
                bits=63,
                constraints={"min": 0, "max": 2**63 - 1},
                nullable=False,
            )
        ]

        original = {"max_field": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=99, max_value=100))
    def test_off_by_one_boundary(self, value):
        """Off-by-one errors at boundaries are handled correctly."""
        layouts = [
            FieldLayout(
                name="edge_case",
                type="integer",
                offset=0,
                bits=1,  # 2 values (99, 100)
                constraints={"min": 99, "max": 100},
                nullable=False,
            )
        ]

        original = {"edge_case": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
        st.integers(min_value=0, max_value=255),
    )
    def test_multiple_max_values_simultaneously(self, v1, v2, v3):
        """Multiple fields at max values don't interfere."""
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
            FieldLayout(
                name="field3",
                type="integer",
                offset=16,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
        ]

        original = {"field1": v1, "field2": v2, "field3": v3}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestEnumBoundaries:
    """Boundary condition tests for enum fields."""

    @settings(max_examples=500)
    @given(st.sampled_from(["only"]))
    def test_single_value_enum_zero_bits(self, value):
        """Single-value enum (0 bits) round-trips correctly."""
        layouts = [
            FieldLayout(
                name="constant",
                type="enum",
                offset=0,
                bits=0,
                constraints={"values": ["only"]},
                nullable=False,
            )
        ]

        original = {"constant": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.sampled_from(["yes", "no"]))
    def test_two_value_enum_one_bit(self, value):
        """Two-value enum (1 bit) handles both values."""
        layouts = [
            FieldLayout(
                name="binary_choice",
                type="enum",
                offset=0,
                bits=1,
                constraints={"values": ["yes", "no"]},
                nullable=False,
            )
        ]

        original = {"binary_choice": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=0, max_value=255))
    def test_large_enum_256_values(self, index):
        """Large enum with 256 values (8 bits) handles all indices."""
        values = [f"value_{i}" for i in range(256)]
        layouts = [
            FieldLayout(
                name="large_enum",
                type="enum",
                offset=0,
                bits=8,
                constraints={"values": values},
                nullable=False,
            )
        ]

        original = {"large_enum": values[index]}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.sampled_from(["a", "b", "c", "d"]))
    def test_enum_last_value_boundary(self, value):
        """Enum index at exact max boundary (last value)."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            )
        ]

        original = {"status": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.sampled_from(["x", "y", "z"]))
    def test_enum_power_of_two_minus_one(self, value):
        """Enum with 3 values (2 bits, not power of 2) works correctly."""
        layouts = [
            FieldLayout(
                name="choice",
                type="enum",
                offset=0,
                bits=2,  # 3 values need 2 bits (not fully utilized)
                constraints={"values": ["x", "y", "z"]},
                nullable=False,
            )
        ]

        original = {"choice": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestBooleanBoundaries:
    """Boundary condition tests for boolean fields."""

    @settings(max_examples=500)
    @given(st.booleans())
    def test_boolean_at_offset_zero(self, value):
        """Boolean at offset 0 (LSB) round-trips correctly."""
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
    @given(st.booleans())
    def test_boolean_at_high_offset(self, value):
        """Boolean at high offset (bit 60) round-trips correctly."""
        layouts = [
            FieldLayout(
                name="high_flag",
                type="boolean",
                offset=60,
                bits=1,
                constraints={},
                nullable=False,
            )
        ]

        original = {"high_flag": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.booleans(), st.booleans(), st.booleans(), st.booleans())
    def test_multiple_booleans_adjacent(self, b1, b2, b3, b4):
        """Multiple adjacent booleans don't interfere."""
        layouts = [
            FieldLayout(
                name="flag1",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="flag2",
                type="boolean",
                offset=1,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="flag3",
                type="boolean",
                offset=2,
                bits=1,
                constraints={},
                nullable=False,
            ),
            FieldLayout(
                name="flag4",
                type="boolean",
                offset=3,
                bits=1,
                constraints={},
                nullable=False,
            ),
        ]

        original = {"flag1": b1, "flag2": b2, "flag3": b3, "flag4": b4}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original


class TestNullableBoundaries:
    """Boundary condition tests for nullable field combinations."""

    @settings(max_examples=500)
    @given(st.none() | st.booleans())
    def test_nullable_boolean_both_states(self, value):
        """Nullable boolean handles None, True, False correctly."""
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
    @given(st.none() | st.integers(min_value=-128, max_value=127))
    def test_nullable_int_at_boundaries(self, value):
        """Nullable integer handles None and min/max values."""
        layouts = [
            FieldLayout(
                name="optional_int",
                type="integer",
                offset=0,
                bits=9,  # 1 presence + 8 value
                constraints={"min": -128, "max": 127},
                nullable=True,
            )
        ]

        original = {"optional_int": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.none() | st.sampled_from(["only"]))
    def test_nullable_single_value_enum(self, value):
        """Nullable single-value enum (1 presence bit only)."""
        layouts = [
            FieldLayout(
                name="optional_constant",
                type="enum",
                offset=0,
                bits=1,  # 1 presence + 0 value
                constraints={"values": ["only"]},
                nullable=True,
            )
        ]

        original = {"optional_constant": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(
        st.none() | st.integers(min_value=0, max_value=100),
        st.none() | st.integers(min_value=0, max_value=100),
        st.none() | st.integers(min_value=0, max_value=100),
    )
    def test_all_fields_nullable_mixed_none(self, v1, v2, v3):
        """All fields nullable with mixed None/present values."""
        layouts = [
            FieldLayout(
                name="field1",
                type="integer",
                offset=0,
                bits=8,  # 1 presence + 7 value
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="field2",
                type="integer",
                offset=8,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="field3",
                type="integer",
                offset=16,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
        ]

        original = {"field1": v1, "field2": v2, "field3": v3}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.booleans())
    def test_all_nullable_fields_none(self, flag_value):
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
        ]

        original = {"flag": flag_value, "opt1": None, "opt2": None}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.none() | st.booleans())
    def test_nullable_at_different_offsets(self, value):
        """Nullable field at different bit offsets works correctly."""
        # Test at offset 0
        layouts_offset_0 = [
            FieldLayout(
                name="opt_flag",
                type="boolean",
                offset=0,
                bits=2,
                constraints={},
                nullable=True,
            )
        ]

        original = {"opt_flag": value}
        encoded = encode(original, layouts_offset_0)
        decoded = decode(encoded, layouts_offset_0)
        assert decoded == original

        # Test at offset 30
        layouts_offset_30 = [
            FieldLayout(
                name="padding",
                type="integer",
                offset=0,
                bits=30,
                constraints={"min": 0, "max": 2**30 - 1},
                nullable=False,
            ),
            FieldLayout(
                name="opt_flag",
                type="boolean",
                offset=30,
                bits=2,
                constraints={},
                nullable=True,
            ),
        ]

        original = {"padding": 0, "opt_flag": value}
        encoded = encode(original, layouts_offset_30)
        decoded = decode(encoded, layouts_offset_30)
        assert decoded == original


class TestCombinedBoundaries:
    """Combined boundary tests across multiple field types."""

    @settings(max_examples=500)
    @given(
        st.booleans(),
        st.integers(min_value=0, max_value=255),
        st.sampled_from(["a", "b", "c", "d"]),
        st.none() | st.integers(min_value=-100, max_value=100),
    )
    def test_all_field_types_combined(self, bool_val, int_val, enum_val, nullable_val):
        """All field types combined in single schema."""
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
                name="counter",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 255},
                nullable=False,
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=9,
                bits=2,
                constraints={"values": ["a", "b", "c", "d"]},
                nullable=False,
            ),
            FieldLayout(
                name="optional_score",
                type="integer",
                offset=11,
                bits=9,  # 1 presence + 8 value
                constraints={"min": -100, "max": 100},
                nullable=True,
            ),
        ]

        original = {
            "flag": bool_val,
            "counter": int_val,
            "status": enum_val,
            "optional_score": nullable_val,
        }
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original

    @settings(max_examples=500)
    @given(st.integers(min_value=0, max_value=2**16 - 1))
    def test_field_spanning_byte_boundary(self, value):
        """Field that spans byte boundary encodes/decodes correctly."""
        layouts = [
            FieldLayout(
                name="spanning_field",
                type="integer",
                offset=4,  # Starts at bit 4, spans into second byte
                bits=16,
                constraints={"min": 0, "max": 2**16 - 1},
                nullable=False,
            )
        ]

        original = {"spanning_field": value}
        encoded = encode(original, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == original
