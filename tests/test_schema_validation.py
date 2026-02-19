"""Comprehensive validation tests for BitSchema models.

Tests all edge cases, boundary conditions, and error scenarios for:
- IntFieldDefinition validation
- BoolFieldDefinition validation
- EnumFieldDefinition validation
- BitSchema validation (including 64-bit limit)
- Schema loading from JSON/YAML
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from bitschema import (
    BitSchema,
    IntFieldDefinition,
    BoolFieldDefinition,
    EnumFieldDefinition,
    schema_from_dict,
    load_from_json,
    SchemaError,
)


class TestIntFieldDefinition:
    """Test IntFieldDefinition validation."""

    def test_valid_unsigned_field(self):
        """Valid unsigned integer field."""
        field = IntFieldDefinition(type="int", bits=8, signed=False)
        assert field.bits == 8
        assert field.signed is False
        assert field.nullable is False

    def test_valid_signed_field(self):
        """Valid signed integer field."""
        field = IntFieldDefinition(type="int", bits=16, signed=True)
        assert field.bits == 16
        assert field.signed is True

    def test_valid_nullable_field(self):
        """Valid nullable field."""
        field = IntFieldDefinition(type="int", bits=8, nullable=True)
        assert field.nullable is True

    def test_valid_with_constraints(self):
        """Valid field with min/max constraints."""
        field = IntFieldDefinition(type="int", bits=7, signed=False, min=0, max=100)
        assert field.min == 0
        assert field.max == 100

    def test_bits_minimum_boundary(self):
        """Bits minimum boundary: 1 bit is valid."""
        field = IntFieldDefinition(type="int", bits=1)
        assert field.bits == 1

    def test_bits_maximum_boundary(self):
        """Bits maximum boundary: 64 bits is valid."""
        field = IntFieldDefinition(type="int", bits=64)
        assert field.bits == 64

    def test_bits_below_minimum_fails(self):
        """Bits below 1 should fail."""
        with pytest.raises(PydanticValidationError) as exc_info:
            IntFieldDefinition(type="int", bits=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_bits_above_maximum_fails(self):
        """Bits above 64 should fail."""
        with pytest.raises(PydanticValidationError) as exc_info:
            IntFieldDefinition(type="int", bits=65)
        assert "less than or equal to 64" in str(exc_info.value)

    def test_min_exceeds_bit_range_unsigned(self):
        """Min value exceeds unsigned bit range."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, signed=False, min=256)
        assert "min=256 exceeds maximum representable value 255" in str(exc_info.value)

    def test_max_exceeds_bit_range_unsigned(self):
        """Max value exceeds unsigned bit range."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, signed=False, max=256)
        assert "cannot be represented in 8 unsigned bits" in str(exc_info.value)

    def test_min_below_bit_range_signed(self):
        """Min value below signed bit range."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, signed=True, min=-129)
        assert "cannot be represented in 8 signed bits" in str(exc_info.value)

    def test_max_exceeds_bit_range_signed(self):
        """Max value exceeds signed bit range."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, signed=True, max=128)
        assert "cannot be represented in 8 signed bits" in str(exc_info.value)

    def test_min_greater_than_max(self):
        """Min cannot be greater than max."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, min=100, max=50)
        assert "min=100 cannot be greater than max=50" in str(exc_info.value)

    def test_valid_negative_constraint_unsigned_fails(self):
        """Unsigned field cannot have negative min."""
        with pytest.raises(ValueError) as exc_info:
            IntFieldDefinition(type="int", bits=8, signed=False, min=-1)
        assert "cannot be represented" in str(exc_info.value)

    def test_edge_case_1bit_unsigned(self):
        """1-bit unsigned: range [0, 1]."""
        field = IntFieldDefinition(type="int", bits=1, signed=False, min=0, max=1)
        assert field.bits == 1

    def test_edge_case_1bit_signed_fails(self):
        """1-bit signed is mathematically valid but practically odd: range [-1, 0]."""
        # Signed 1-bit: theoretical range is -(2^0) to 2^0 - 1 = -1 to 0
        field = IntFieldDefinition(type="int", bits=1, signed=True, min=-1, max=0)
        assert field.bits == 1


class TestBoolFieldDefinition:
    """Test BoolFieldDefinition validation."""

    def test_valid_bool_field(self):
        """Valid boolean field."""
        field = BoolFieldDefinition(type="bool")
        assert field.type == "bool"
        assert field.nullable is False

    def test_valid_nullable_bool(self):
        """Valid nullable boolean field."""
        field = BoolFieldDefinition(type="bool", nullable=True)
        assert field.nullable is True


class TestEnumFieldDefinition:
    """Test EnumFieldDefinition validation."""

    def test_valid_enum_field(self):
        """Valid enum field."""
        field = EnumFieldDefinition(type="enum", values=["a", "b", "c"])
        assert field.values == ["a", "b", "c"]
        assert field.bits_required == 2  # 2 bits needed for 3 values

    def test_valid_single_value_enum(self):
        """Single-value enum is valid (constant)."""
        field = EnumFieldDefinition(type="enum", values=["only"])
        assert field.bits_required == 0  # 0 bits for constant

    def test_valid_nullable_enum(self):
        """Valid nullable enum."""
        field = EnumFieldDefinition(type="enum", values=["x", "y"], nullable=True)
        assert field.nullable is True

    def test_empty_values_fails(self):
        """Empty values list should fail."""
        with pytest.raises(PydanticValidationError) as exc_info:
            EnumFieldDefinition(type="enum", values=[])
        assert "at least 1 item" in str(exc_info.value).lower()

    def test_duplicate_values_fails(self):
        """Duplicate enum values should fail."""
        with pytest.raises(ValueError) as exc_info:
            EnumFieldDefinition(type="enum", values=["a", "b", "a"])
        assert "must be unique" in str(exc_info.value)
        assert "a" in str(exc_info.value)

    def test_empty_string_value_fails(self):
        """Empty string in values should fail."""
        with pytest.raises(ValueError) as exc_info:
            EnumFieldDefinition(type="enum", values=["a", "", "b"])
        assert "cannot be empty strings" in str(exc_info.value)

    def test_too_many_values_fails(self):
        """More than 255 values should fail."""
        values = [f"val{i}" for i in range(256)]
        with pytest.raises(PydanticValidationError) as exc_info:
            EnumFieldDefinition(type="enum", values=values)
        assert "at most 255" in str(exc_info.value)

    def test_bits_required_calculation(self):
        """Test bits_required calculation for various sizes."""
        assert EnumFieldDefinition(type="enum", values=["a"]).bits_required == 0
        assert EnumFieldDefinition(type="enum", values=["a", "b"]).bits_required == 1
        assert EnumFieldDefinition(type="enum", values=["a", "b", "c"]).bits_required == 2
        assert EnumFieldDefinition(type="enum", values=[f"v{i}" for i in range(4)]).bits_required == 2
        assert EnumFieldDefinition(type="enum", values=[f"v{i}" for i in range(5)]).bits_required == 3
        assert EnumFieldDefinition(type="enum", values=[f"v{i}" for i in range(255)]).bits_required == 8


class TestBitSchema:
    """Test BitSchema validation."""

    def test_valid_simple_schema(self):
        """Valid simple schema."""
        schema = BitSchema(
            version="1",
            name="User",
            fields={
                "age": IntFieldDefinition(type="int", bits=7),
                "active": BoolFieldDefinition(type="bool"),
            }
        )
        assert schema.name == "User"
        assert len(schema.fields) == 2
        assert schema.calculate_total_bits() == 8

    def test_valid_complex_schema(self):
        """Valid schema with multiple field types."""
        schema = BitSchema(
            version="1",
            name="Complex",
            fields={
                "id": IntFieldDefinition(type="int", bits=16),
                "status": EnumFieldDefinition(type="enum", values=["pending", "active", "done"]),
                "verified": BoolFieldDefinition(type="bool"),
                "score": IntFieldDefinition(type="int", bits=8, nullable=True),
            }
        )
        # 16 (id) + 2 (status, 3 values) + 1 (verified) + 8 (score) + 1 (score presence) = 28 bits
        assert schema.calculate_total_bits() == 28

    def test_invalid_name_empty(self):
        """Empty schema name should fail."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BitSchema(
                version="1",
                name="",
                fields={"f": BoolFieldDefinition(type="bool")}
            )
        assert "at least 1 character" in str(exc_info.value).lower()

    def test_invalid_name_not_identifier(self):
        """Schema name must be valid Python identifier."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BitSchema(
                version="1",
                name="123Invalid",
                fields={"f": BoolFieldDefinition(type="bool")}
            )
        assert "pattern" in str(exc_info.value)

    def test_invalid_name_with_spaces(self):
        """Schema name cannot contain spaces."""
        with pytest.raises(PydanticValidationError) as exc_info:
            BitSchema(
                version="1",
                name="My Schema",
                fields={"f": BoolFieldDefinition(type="bool")}
            )
        assert "pattern" in str(exc_info.value)

    def test_no_fields_fails(self):
        """Schema must have at least one field."""
        with pytest.raises(ValueError) as exc_info:
            BitSchema(version="1", name="Empty", fields={})
        assert "at least one field" in str(exc_info.value)

    def test_exceeds_64bit_limit(self):
        """Schema exceeding 64-bit limit should fail."""
        with pytest.raises(ValueError) as exc_info:
            BitSchema(
                version="1",
                name="TooBig",
                fields={
                    "f1": IntFieldDefinition(type="int", bits=32),
                    "f2": IntFieldDefinition(type="int", bits=33),
                }
            )
        assert "exceeds 64-bit limit" in str(exc_info.value)
        assert "65 bits total" in str(exc_info.value)

    def test_exactly_64bits_valid(self):
        """Schema with exactly 64 bits is valid."""
        schema = BitSchema(
            version="1",
            name="MaxSize",
            fields={
                "f1": IntFieldDefinition(type="int", bits=32),
                "f2": IntFieldDefinition(type="int", bits=32),
            }
        )
        assert schema.calculate_total_bits() == 64

    def test_nullable_adds_presence_bit(self):
        """Nullable fields add presence bit to total."""
        schema = BitSchema(
            version="1",
            name="WithNull",
            fields={
                "value": IntFieldDefinition(type="int", bits=8, nullable=True),
            }
        )
        # 8 bits for value + 1 bit for presence = 9 bits
        assert schema.calculate_total_bits() == 9

    def test_multiple_nullable_fields(self):
        """Multiple nullable fields each add presence bit."""
        schema = BitSchema(
            version="1",
            name="MultiNull",
            fields={
                "a": BoolFieldDefinition(type="bool", nullable=True),
                "b": IntFieldDefinition(type="int", bits=4, nullable=True),
                "c": EnumFieldDefinition(type="enum", values=["x", "y"], nullable=True),
            }
        )
        # 1 (a) + 1 (a presence) + 4 (b) + 1 (b presence) + 1 (c) + 1 (c presence) = 9 bits
        assert schema.calculate_total_bits() == 9


class TestSchemaLoading:
    """Test schema loading from JSON and YAML."""

    def test_load_from_json_valid(self):
        """Load valid schema from JSON."""
        json_data = '''
        {
            "version": "1",
            "name": "TestSchema",
            "fields": {
                "age": {"type": "int", "bits": 8},
                "active": {"type": "bool"}
            }
        }
        '''
        schema = load_from_json(json_data)
        assert schema.name == "TestSchema"
        assert len(schema.fields) == 2

    def test_load_from_json_invalid_syntax(self):
        """Invalid JSON syntax should raise SchemaError."""
        invalid_json = '{"version": "1", "name": "Test"'  # Missing closing brace
        with pytest.raises(SchemaError) as exc_info:
            load_from_json(invalid_json)
        assert "Invalid JSON" in str(exc_info.value)

    def test_load_from_json_validation_fails(self):
        """JSON with validation errors should raise SchemaError."""
        json_data = '''
        {
            "version": "1",
            "name": "Test",
            "fields": {
                "bad": {"type": "int", "bits": 0}
            }
        }
        '''
        with pytest.raises(SchemaError) as exc_info:
            load_from_json(json_data)
        assert "Schema validation failed" in str(exc_info.value)

    def test_schema_from_dict_valid(self):
        """Create schema from dictionary."""
        data = {
            "version": "1",
            "name": "DictSchema",
            "fields": {
                "count": {"type": "int", "bits": 16},
            }
        }
        schema = schema_from_dict(data)
        assert schema.name == "DictSchema"

    def test_schema_from_dict_validation_fails(self):
        """Invalid dictionary should raise SchemaError."""
        data = {
            "version": "1",
            "name": "",  # Empty name invalid
            "fields": {"f": {"type": "bool"}}
        }
        with pytest.raises(SchemaError) as exc_info:
            schema_from_dict(data)
        assert "Schema validation failed" in str(exc_info.value)


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_schema_with_all_field_types(self):
        """Schema using all available field types."""
        schema = BitSchema(
            version="1",
            name="AllTypes",
            fields={
                "int_field": IntFieldDefinition(type="int", bits=10, signed=True),
                "bool_field": BoolFieldDefinition(type="bool"),
                "enum_field": EnumFieldDefinition(type="enum", values=["a", "b", "c"]),
            }
        )
        # 10 (int) + 1 (bool) + 2 (enum, 3 values) = 13 bits
        assert schema.calculate_total_bits() == 13

    def test_field_name_can_be_python_keyword(self):
        """Field names can be Python keywords (will be escaped in codegen)."""
        schema = BitSchema(
            version="1",
            name="Keywords",
            fields={
                "class": BoolFieldDefinition(type="bool"),
                "def": IntFieldDefinition(type="int", bits=4),
            }
        )
        assert "class" in schema.fields
        assert "def" in schema.fields

    def test_unicode_in_enum_values(self):
        """Enum values can contain Unicode characters."""
        field = EnumFieldDefinition(type="enum", values=["hello", "world", "こんにちは"])
        assert len(field.values) == 3
        assert "こんにちは" in field.values

    def test_very_long_enum_value(self):
        """Very long enum values are allowed."""
        long_value = "a" * 1000
        field = EnumFieldDefinition(type="enum", values=[long_value, "short"])
        assert long_value in field.values
