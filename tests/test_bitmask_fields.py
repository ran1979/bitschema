"""TDD tests for bitmask field type functionality.

Tests cover schema validation, bit calculation, encoding, decoding,
and round-trip correctness for bitmask fields.
"""

import pytest
from hypothesis import given, strategies as st

from bitschema.models import BitSchema
from bitschema.layout import compute_bit_layout, FieldLayout
from bitschema.encoder import encode
from bitschema.decoder import decode


class TestBitmaskSchemaValidation:
    """Test bitmask field schema validation."""

    def test_bitmask_field_valid_schema(self):
        """Valid bitmask field schema should load successfully."""
        schema_dict = {
            "version": "1",
            "name": "Permissions",
            "fields": {
                "perms": {
                    "type": "bitmask",
                    "flags": {
                        "read": 0,
                        "write": 1,
                        "execute": 2,
                        "delete": 3,
                    },
                    "nullable": False,
                }
            }
        }
        schema = BitSchema(**schema_dict)
        assert schema.name == "Permissions"
        assert "perms" in schema.fields

    def test_bitmask_requires_at_least_one_flag(self):
        """Bitmask field must have at least one flag."""
        schema_dict = {
            "version": "1",
            "name": "Test",
            "fields": {
                "empty_mask": {
                    "type": "bitmask",
                    "flags": {},
                    "nullable": False,
                }
            }
        }
        with pytest.raises(ValueError, match="at least one flag"):
            BitSchema(**schema_dict)

    def test_bitmask_flag_positions_must_be_unique(self):
        """Flag positions must be unique - no two flags at same bit."""
        schema_dict = {
            "version": "1",
            "name": "Test",
            "fields": {
                "perms": {
                    "type": "bitmask",
                    "flags": {
                        "read": 0,
                        "write": 1,
                        "execute": 1,  # Duplicate position
                    },
                    "nullable": False,
                }
            }
        }
        with pytest.raises(ValueError, match="positions must be unique"):
            BitSchema(**schema_dict)

    def test_bitmask_flag_positions_within_64bit_limit(self):
        """Flag positions must be 0-63 for 64-bit limit."""
        schema_dict = {
            "version": "1",
            "name": "Test",
            "fields": {
                "perms": {
                    "type": "bitmask",
                    "flags": {
                        "read": 0,
                        "overflow": 64,  # Exceeds 64-bit limit
                    },
                    "nullable": False,
                }
            }
        }
        with pytest.raises(ValueError, match="positions must be 0-63"):
            BitSchema(**schema_dict)

    def test_bitmask_negative_flag_position(self):
        """Flag positions cannot be negative."""
        schema_dict = {
            "version": "1",
            "name": "Test",
            "fields": {
                "perms": {
                    "type": "bitmask",
                    "flags": {
                        "negative": -1,
                    },
                    "nullable": False,
                }
            }
        }
        with pytest.raises(ValueError, match="positions must be 0-63"):
            BitSchema(**schema_dict)

    def test_bitmask_flag_names_must_be_valid_identifiers(self):
        """Flag names must be valid Python identifiers."""
        schema_dict = {
            "version": "1",
            "name": "Test",
            "fields": {
                "perms": {
                    "type": "bitmask",
                    "flags": {
                        "valid_name": 0,
                        "invalid-name": 1,  # Hyphen not allowed
                    },
                    "nullable": False,
                }
            }
        }
        with pytest.raises(ValueError, match="valid Python identifier"):
            BitSchema(**schema_dict)


class TestBitmaskBitCalculation:
    """Test bit calculation for bitmask fields."""

    def test_bitmask_bits_equals_max_position_plus_one(self):
        """Bits required = max(flag_positions) + 1."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)
        assert len(layouts) == 1
        assert layouts[0].bits == 3  # max(0, 1, 2) + 1 = 3

    def test_bitmask_single_flag_at_position_zero(self):
        """Single flag at position 0 requires 1 bit."""
        fields = [
            {
                "name": "flag",
                "type": "bitmask",
                "flags": {"enabled": 0},
                "nullable": False,
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)
        assert layouts[0].bits == 1  # max(0) + 1 = 1

    def test_bitmask_sparse_positions(self):
        """Sparse flag positions still require bits up to max."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "admin": 7},  # Gaps in positions
                "nullable": False,
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)
        assert layouts[0].bits == 8  # max(0, 7) + 1 = 8


class TestBitmaskEncoding:
    """Test bitmask field encoding."""

    def test_encode_single_flag_set(self):
        """Encoding with single flag set to True."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"perms": {"read": True, "write": False}}
        encoded = encode(data, layouts)

        # read at position 0: bit 0 = 1
        # write at position 1: bit 1 = 0
        # Result: 0b01 = 1
        assert encoded == 1

    def test_encode_multiple_flags_set(self):
        """Encoding with multiple flags set to True."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"perms": {"read": True, "write": False, "execute": True}}
        encoded = encode(data, layouts)

        # read at position 0: bit 0 = 1
        # write at position 1: bit 1 = 0
        # execute at position 2: bit 2 = 1
        # Result: 0b101 = 5
        assert encoded == 5

    def test_encode_no_flags_set(self):
        """Encoding with all flags set to False."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"perms": {"read": False, "write": False, "execute": False}}
        encoded = encode(data, layouts)

        # All flags False: all bits 0
        # Result: 0b000 = 0
        assert encoded == 0

    def test_encode_all_flags_set(self):
        """Encoding with all flags set to True."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"perms": {"read": True, "write": True, "execute": True}}
        encoded = encode(data, layouts)

        # All flags True: all bits 1
        # Result: 0b111 = 7
        assert encoded == 7

    def test_encode_omitted_flags_default_to_false(self):
        """Flags not specified in data dict default to False."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Only specify read flag
        data = {"perms": {"read": True}}
        encoded = encode(data, layouts)

        # read=True, write=False (default), execute=False (default)
        # Result: 0b001 = 1
        assert encoded == 1


class TestBitmaskDecoding:
    """Test bitmask field decoding."""

    def test_decode_single_flag_set(self):
        """Decoding integer to dict with single flag set."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # 0b01 = 1 (read=True, write=False)
        encoded = 1
        decoded = decode(encoded, layouts)

        assert decoded == {"perms": {"read": True, "write": False}}

    def test_decode_multiple_flags_set(self):
        """Decoding integer to dict with multiple flags set."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # 0b101 = 5 (read=True, write=False, execute=True)
        encoded = 5
        decoded = decode(encoded, layouts)

        assert decoded == {"perms": {"read": True, "write": False, "execute": True}}

    def test_decode_no_flags_set(self):
        """Decoding zero to dict with all flags False."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        encoded = 0
        decoded = decode(encoded, layouts)

        assert decoded == {"perms": {"read": False, "write": False, "execute": False}}


class TestBitmaskRoundTrip:
    """Test bitmask field round-trip correctness."""

    def test_roundtrip_various_combinations(self):
        """Encode then decode returns original for various flag combinations."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2, "delete": 3},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        test_cases = [
            {"perms": {"read": True, "write": False, "execute": False, "delete": False}},
            {"perms": {"read": False, "write": True, "execute": False, "delete": False}},
            {"perms": {"read": True, "write": True, "execute": True, "delete": True}},
            {"perms": {"read": False, "write": False, "execute": False, "delete": False}},
            {"perms": {"read": True, "write": False, "execute": True, "delete": False}},
        ]

        for data in test_cases:
            encoded = encode(data, layouts)
            decoded = decode(encoded, layouts)
            assert decoded == data


class TestBitmaskNullable:
    """Test nullable bitmask fields."""

    def test_nullable_bitmask_with_none_value(self):
        """Nullable bitmask field with None value."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1},
                "nullable": True,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Presence bit adds 1 to total bits
        assert layouts[0].bits == 3  # 2 value bits + 1 presence bit

        data = {"perms": None}
        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == {"perms": None}

    def test_nullable_bitmask_with_value(self):
        """Nullable bitmask field with value."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1},
                "nullable": True,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"perms": {"read": True, "write": False}}
        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        assert decoded == data


class TestBitmaskPropertyBased:
    """Property-based tests for bitmask fields using Hypothesis."""

    @given(
        st.dictionaries(
            st.sampled_from(["read", "write", "execute", "delete"]),
            st.booleans(),
            min_size=0,
            max_size=4,
        )
    )
    def test_bitmask_all_combinations_roundtrip(self, flag_values):
        """Property test: all flag combinations round-trip correctly."""
        fields = [
            {
                "name": "perms",
                "type": "bitmask",
                "flags": {"read": 0, "write": 1, "execute": 2, "delete": 3},
                "nullable": False,
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Ensure all flags are in data dict (defaults to False if missing)
        data = {"perms": flag_values}
        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        # Decoded should have all flags with their values (defaults to False)
        expected = {"perms": {
            "read": flag_values.get("read", False),
            "write": flag_values.get("write", False),
            "execute": flag_values.get("execute", False),
            "delete": flag_values.get("delete", False),
        }}
        assert decoded == expected
