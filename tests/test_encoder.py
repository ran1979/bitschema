"""Tests for encoder module - encoding data dict to 64-bit integer.

Tests LSB-first accumulator pattern, normalization of field values,
and nullable field presence bit handling.
"""

import pytest
from bitschema.encoder import encode, normalize_value
from bitschema.layout import FieldLayout
from bitschema.errors import EncodingError


class TestNormalizeValue:
    """Test value normalization for different field types."""

    def test_normalize_boolean_true(self):
        """Boolean True normalizes to 1."""
        layout = FieldLayout(
            name="active", type="boolean", offset=0, bits=1, constraints={}
        )
        assert normalize_value(True, layout) == 1

    def test_normalize_boolean_false(self):
        """Boolean False normalizes to 0."""
        layout = FieldLayout(
            name="active", type="boolean", offset=0, bits=1, constraints={}
        )
        assert normalize_value(False, layout) == 0

    def test_normalize_integer_unsigned(self):
        """Integer with min=0 normalizes by subtracting min."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 127},
        )
        assert normalize_value(42, layout) == 42

    def test_normalize_integer_signed(self):
        """Integer with negative min normalizes to unsigned."""
        layout = FieldLayout(
            name="temp",
            type="integer",
            offset=0,
            bits=5,
            constraints={"min": -10, "max": 10},
        )
        # -5 - (-10) = 5
        assert normalize_value(-5, layout) == 5

    def test_normalize_integer_at_min(self):
        """Integer at minimum normalizes to 0."""
        layout = FieldLayout(
            name="temp",
            type="integer",
            offset=0,
            bits=5,
            constraints={"min": -10, "max": 10},
        )
        assert normalize_value(-10, layout) == 0

    def test_normalize_integer_at_max(self):
        """Integer at maximum normalizes correctly."""
        layout = FieldLayout(
            name="temp",
            type="integer",
            offset=0,
            bits=5,
            constraints={"min": -10, "max": 10},
        )
        # 10 - (-10) = 20
        assert normalize_value(10, layout) == 20

    def test_normalize_enum_first_value(self):
        """Enum first value normalizes to index 0."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["idle", "active", "done"]},
        )
        assert normalize_value("idle", layout) == 0

    def test_normalize_enum_middle_value(self):
        """Enum middle value normalizes to correct index."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["idle", "active", "done"]},
        )
        assert normalize_value("active", layout) == 1

    def test_normalize_enum_last_value(self):
        """Enum last value normalizes to correct index."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["idle", "active", "done"]},
        )
        assert normalize_value("done", layout) == 2


class TestEncodeSingleField:
    """Test encoding single fields at offset 0."""

    def test_encode_boolean_true(self):
        """Encode True at offset 0 returns 1."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={})
        ]
        data = {"active": True}
        assert encode(data, layouts) == 1

    def test_encode_boolean_false(self):
        """Encode False at offset 0 returns 0."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={})
        ]
        data = {"active": False}
        assert encode(data, layouts) == 0

    def test_encode_integer_unsigned(self):
        """Encode unsigned integer at offset 0."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=7,
                constraints={"min": 0, "max": 127},
            )
        ]
        data = {"age": 42}
        assert encode(data, layouts) == 42

    def test_encode_integer_signed(self):
        """Encode signed integer normalizes to unsigned."""
        layouts = [
            FieldLayout(
                name="temp",
                type="integer",
                offset=0,
                bits=5,
                constraints={"min": -10, "max": 10},
            )
        ]
        data = {"temp": -5}
        # -5 - (-10) = 5
        assert encode(data, layouts) == 5

    def test_encode_enum_first(self):
        """Encode enum first value to index 0."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=2,
                constraints={"values": ["idle", "active", "done"]},
            )
        ]
        data = {"status": "idle"}
        assert encode(data, layouts) == 0

    def test_encode_enum_middle(self):
        """Encode enum middle value to correct index."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=2,
                constraints={"values": ["idle", "active", "done"]},
            )
        ]
        data = {"status": "active"}
        assert encode(data, layouts) == 1


class TestEncodeMultipleFields:
    """Test encoding multiple fields with correct offsets."""

    def test_encode_two_booleans(self):
        """Encode two boolean fields at different offsets."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
            FieldLayout(name="enabled", type="boolean", offset=1, bits=1, constraints={}),
        ]
        # active=True (1 at offset 0), enabled=True (1 at offset 1)
        # Binary: 0b11 = 3
        data = {"active": True, "enabled": True}
        assert encode(data, layouts) == 0b11

    def test_encode_boolean_and_integer(self):
        """Encode boolean at offset 0, integer at offset 1."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 127},
            ),
        ]
        # active=True (1 at offset 0), age=42 (42 at offset 1)
        # 1 | (42 << 1) = 1 | 84 = 85
        # Binary: 0b1010101 = 85
        data = {"active": True, "age": 42}
        assert encode(data, layouts) == 85

    def test_encode_three_fields(self):
        """Encode three fields with different types."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 127},
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=8,
                bits=2,
                constraints={"values": ["idle", "active", "done"]},
            ),
        ]
        # active=True (1 at offset 0)
        # age=42 (42 at offset 1)
        # status="done" (2 at offset 8)
        # 1 | (42 << 1) | (2 << 8) = 1 | 84 | 512 = 597
        data = {"active": True, "age": 42, "status": "done"}
        assert encode(data, layouts) == 597


class TestEncodeNullableFields:
    """Test encoding nullable fields with presence bits."""

    def test_encode_nullable_with_none(self):
        """Nullable field with None value has presence bit = 0."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=8,  # 1 presence + 7 value
                constraints={"min": 0, "max": 127},
                nullable=True,
            )
        ]
        data = {"age": None}
        # Presence bit = 0, value bits = 0
        assert encode(data, layouts) == 0

    def test_encode_nullable_with_value(self):
        """Nullable field with value has presence bit = 1."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=8,  # 1 presence + 7 value
                constraints={"min": 0, "max": 127},
                nullable=True,
            )
        ]
        data = {"age": 42}
        # Presence bit = 1 at offset 0, value = 42 at offset 1
        # 1 | (42 << 1) = 1 | 84 = 85
        assert encode(data, layouts) == 85

    def test_encode_nullable_boolean(self):
        """Nullable boolean with value."""
        layouts = [
            FieldLayout(
                name="active",
                type="boolean",
                offset=0,
                bits=2,  # 1 presence + 1 value
                constraints={},
                nullable=True,
            )
        ]
        data = {"active": True}
        # Presence = 1 at offset 0, value = 1 at offset 1
        # 1 | (1 << 1) = 1 | 2 = 3
        assert encode(data, layouts) == 3

    def test_encode_nullable_enum(self):
        """Nullable enum with value."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=3,  # 1 presence + 2 value
                constraints={"values": ["idle", "active", "done"]},
                nullable=True,
            )
        ]
        data = {"status": "active"}
        # Presence = 1 at offset 0, value = 1 (index of "active") at offset 1
        # 1 | (1 << 1) = 1 | 2 = 3
        assert encode(data, layouts) == 3

    def test_encode_nullable_and_regular_field(self):
        """Encode mix of nullable and regular fields."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
            FieldLayout(
                name="score",
                type="integer",
                offset=1,
                bits=8,  # 1 presence + 7 value
                constraints={"min": 0, "max": 127},
                nullable=True,
            ),
        ]
        # active=False (0 at offset 0)
        # score=None (presence=0 at offset 1, value=0 at offset 2)
        data = {"active": False, "score": None}
        assert encode(data, layouts) == 0


class TestEncodeValidation:
    """Test that encoding validates data before packing."""

    def test_encode_validates_before_packing(self):
        """Encode calls validation and fails on invalid data."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=7,
                constraints={"min": 0, "max": 127},
            )
        ]
        data = {"age": 200}  # Exceeds max
        with pytest.raises(EncodingError, match="exceeds maximum"):
            encode(data, layouts)

    def test_encode_missing_required_field(self):
        """Encode fails on missing required field."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 127},
            ),
        ]
        data = {"active": True}  # Missing age
        with pytest.raises(EncodingError, match="missing"):
            encode(data, layouts)

    def test_encode_wrong_type(self):
        """Encode fails on wrong type."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=7,
                constraints={"min": 0, "max": 127},
            )
        ]
        data = {"age": "forty-two"}  # Wrong type
        with pytest.raises(EncodingError, match="expected integer"):
            encode(data, layouts)


class TestEncodeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_encode_zero_bits_enum(self):
        """Single-value enum requires 0 bits."""
        layouts = [
            FieldLayout(
                name="constant",
                type="enum",
                offset=0,
                bits=0,
                constraints={"values": ["only"]},
            )
        ]
        data = {"constant": "only"}
        assert encode(data, layouts) == 0

    def test_encode_max_value_fits_in_bits(self):
        """Max value fits exactly in allocated bits."""
        layouts = [
            FieldLayout(
                name="value",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 255},
            )
        ]
        data = {"value": 255}
        assert encode(data, layouts) == 255

    def test_encode_extra_fields_ignored(self):
        """Extra fields in data dict are ignored."""
        layouts = [
            FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={})
        ]
        data = {"active": True, "extra": "ignored"}
        assert encode(data, layouts) == 1
