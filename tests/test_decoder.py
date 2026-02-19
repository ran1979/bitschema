"""Tests for bit-unpacking decoder.

Verifies decoder extracts bits from 64-bit integer and converts to semantic values.
Tests boolean, integer, enum, and nullable field decoding.
"""

import pytest

from bitschema.decoder import decode, denormalize_value
from bitschema.layout import FieldLayout


class TestDenormalizeValue:
    """Test denormalization of extracted bits to semantic values."""

    def test_denormalize_boolean_true(self):
        """Boolean value 1 denormalizes to True."""
        layout = FieldLayout(
            name="active",
            type="boolean",
            offset=0,
            bits=1,
            constraints={},
            nullable=False,
        )
        assert denormalize_value(1, layout) is True

    def test_denormalize_boolean_false(self):
        """Boolean value 0 denormalizes to False."""
        layout = FieldLayout(
            name="active",
            type="boolean",
            offset=0,
            bits=1,
            constraints={},
            nullable=False,
        )
        assert denormalize_value(0, layout) is False

    def test_denormalize_integer_unsigned(self):
        """Integer in [0, 127] range denormalizes correctly."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 127},
            nullable=False,
        )
        assert denormalize_value(42, layout) == 42
        assert denormalize_value(0, layout) == 0
        assert denormalize_value(127, layout) == 127

    def test_denormalize_integer_signed(self):
        """Integer in [-10, 10] range denormalizes correctly (adds min)."""
        layout = FieldLayout(
            name="temp",
            type="integer",
            offset=0,
            bits=5,
            constraints={"min": -10, "max": 10},
            nullable=False,
        )
        # Extracted value 0 → -10 (min)
        assert denormalize_value(0, layout) == -10
        # Extracted value 10 → 0 (min + 10)
        assert denormalize_value(10, layout) == 0
        # Extracted value 20 → 10 (max)
        assert denormalize_value(20, layout) == 10

    def test_denormalize_enum(self):
        """Enum index denormalizes to string value."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["idle", "active", "done"]},
            nullable=False,
        )
        assert denormalize_value(0, layout) == "idle"
        assert denormalize_value(1, layout) == "active"
        assert denormalize_value(2, layout) == "done"


class TestDecodeSingleField:
    """Test decoding single fields from 64-bit integer."""

    def test_decode_boolean_true(self):
        """Decode boolean True from bit 0."""
        layouts = [
            FieldLayout(
                name="active",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            )
        ]
        # Encoded: 0b1 (bit 0 = 1)
        result = decode(1, layouts)
        assert result == {"active": True}

    def test_decode_boolean_false(self):
        """Decode boolean False from bit 0."""
        layouts = [
            FieldLayout(
                name="active",
                type="boolean",
                offset=0,
                bits=1,
                constraints={},
                nullable=False,
            )
        ]
        # Encoded: 0b0 (bit 0 = 0)
        result = decode(0, layouts)
        assert result == {"active": False}

    def test_decode_integer_unsigned(self):
        """Decode unsigned integer from bits."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=7,
                constraints={"min": 0, "max": 127},
                nullable=False,
            )
        ]
        # Encoded: 42 (0b0101010)
        result = decode(42, layouts)
        assert result == {"age": 42}

    def test_decode_integer_signed(self):
        """Decode signed integer with denormalization."""
        layouts = [
            FieldLayout(
                name="temp",
                type="integer",
                offset=0,
                bits=5,
                constraints={"min": -10, "max": 10},
                nullable=False,
            )
        ]
        # Encoded: 5 (stored as 5, denormalizes to -10 + 5 = -5)
        result = decode(5, layouts)
        assert result == {"temp": -5}

    def test_decode_enum(self):
        """Decode enum index to string value."""
        layouts = [
            FieldLayout(
                name="status",
                type="enum",
                offset=0,
                bits=2,
                constraints={"values": ["idle", "active", "done"]},
                nullable=False,
            )
        ]
        # Encoded: 1 (index 1 → "active")
        result = decode(1, layouts)
        assert result == {"status": "active"}


class TestDecodeMultipleFields:
    """Test decoding multiple fields at different offsets."""

    def test_decode_two_fields(self):
        """Decode boolean and integer from different offsets."""
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
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 127},
                nullable=False,
            ),
        ]
        # Encoded: 0b1010101 (85)
        # Bit 0: 1 (active = True)
        # Bits 1-7: 42 (age = 42)
        # Calculation: (42 << 1) | 1 = 84 + 1 = 85
        result = decode(85, layouts)
        assert result == {"active": True, "age": 42}

    def test_decode_three_fields(self):
        """Decode boolean, integer, and enum."""
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
                bits=4,
                constraints={"min": 0, "max": 15},
                nullable=False,
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=5,
                bits=2,
                constraints={"values": ["idle", "active", "done"]},
                nullable=False,
            ),
        ]
        # Encoded:
        # Bit 0: 1 (active = True)
        # Bits 1-4: 7 (count = 7)
        # Bits 5-6: 2 (status = "done")
        # Calculation: (2 << 5) | (7 << 1) | 1 = 64 + 14 + 1 = 79
        result = decode(79, layouts)
        assert result == {"active": True, "count": 7, "status": "done"}


class TestDecodeNullableFields:
    """Test decoding nullable fields with presence bit."""

    def test_decode_nullable_field_none(self):
        """Nullable field with presence bit = 0 decodes to None."""
        layouts = [
            FieldLayout(
                name="optional_age",
                type="integer",
                offset=0,
                bits=8,  # 1 presence bit + 7 value bits
                constraints={"min": 0, "max": 127},
                nullable=True,
            )
        ]
        # Encoded: 0 (presence bit = 0)
        result = decode(0, layouts)
        assert result == {"optional_age": None}

    def test_decode_nullable_field_with_value(self):
        """Nullable field with presence bit = 1 decodes to value."""
        layouts = [
            FieldLayout(
                name="optional_age",
                type="integer",
                offset=0,
                bits=8,  # 1 presence bit + 7 value bits
                constraints={"min": 0, "max": 127},
                nullable=True,
            )
        ]
        # Encoded: presence bit = 1 at offset 0, value = 42 at offset 1
        # Calculation: (42 << 1) | 1 = 84 + 1 = 85
        result = decode(85, layouts)
        assert result == {"optional_age": 42}

    def test_decode_nullable_boolean_none(self):
        """Nullable boolean with presence = 0 decodes to None."""
        layouts = [
            FieldLayout(
                name="optional_flag",
                type="boolean",
                offset=0,
                bits=2,  # 1 presence bit + 1 boolean bit
                constraints={},
                nullable=True,
            )
        ]
        # Encoded: 0 (presence bit = 0)
        result = decode(0, layouts)
        assert result == {"optional_flag": None}

    def test_decode_nullable_boolean_true(self):
        """Nullable boolean with presence = 1, value = 1 decodes to True."""
        layouts = [
            FieldLayout(
                name="optional_flag",
                type="boolean",
                offset=0,
                bits=2,  # 1 presence bit + 1 boolean bit
                constraints={},
                nullable=True,
            )
        ]
        # Encoded: presence bit = 1 at offset 0, value = 1 at offset 1
        # Calculation: (1 << 1) | 1 = 2 + 1 = 3
        result = decode(3, layouts)
        assert result == {"optional_flag": True}

    def test_decode_nullable_boolean_false(self):
        """Nullable boolean with presence = 1, value = 0 decodes to False."""
        layouts = [
            FieldLayout(
                name="optional_flag",
                type="boolean",
                offset=0,
                bits=2,  # 1 presence bit + 1 boolean bit
                constraints={},
                nullable=True,
            )
        ]
        # Encoded: presence bit = 1 at offset 0, value = 0 at offset 1
        # Calculation: (0 << 1) | 1 = 0 + 1 = 1
        result = decode(1, layouts)
        assert result == {"optional_flag": False}

    def test_decode_mixed_nullable_and_required(self):
        """Decode mix of nullable and required fields."""
        layouts = [
            FieldLayout(
                name="id",
                type="integer",
                offset=0,
                bits=4,
                constraints={"min": 0, "max": 15},
                nullable=False,
            ),
            FieldLayout(
                name="optional_count",
                type="integer",
                offset=4,
                bits=5,  # 1 presence bit + 4 value bits
                constraints={"min": 0, "max": 15},
                nullable=True,
            ),
        ]
        # Encoded:
        # Bits 0-3: 5 (id = 5)
        # Bit 4: 0 (optional_count presence = 0, value = None)
        # Calculation: 5
        result = decode(5, layouts)
        assert result == {"id": 5, "optional_count": None}

        # Encoded:
        # Bits 0-3: 5 (id = 5)
        # Bit 4: 1 (optional_count presence = 1)
        # Bits 5-8: 7 (optional_count value = 7)
        # Calculation: (7 << 5) | (1 << 4) | 5 = 224 + 16 + 5 = 245
        result = decode(245, layouts)
        assert result == {"id": 5, "optional_count": 7}
