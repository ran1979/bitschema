"""Tests for runtime data validation module.

Tests validate_data and validate_field_value functions that check
data dict values against FieldLayout constraints before encoding.
"""

import pytest

from bitschema.layout import FieldLayout
from bitschema.errors import EncodingError
from bitschema.validator import validate_data, validate_field_value


class TestValidateFieldValue:
    """Test validate_field_value function for single field validation."""

    def test_boolean_valid_true(self):
        """Boolean field with True value passes validation."""
        layout = FieldLayout(
            name="active", type="boolean", offset=0, bits=1, constraints={}
        )
        validate_field_value(True, layout)  # Should not raise

    def test_boolean_valid_false(self):
        """Boolean field with False value passes validation."""
        layout = FieldLayout(
            name="active", type="boolean", offset=0, bits=1, constraints={}
        )
        validate_field_value(False, layout)  # Should not raise

    def test_boolean_invalid_type(self):
        """Boolean field with non-bool value raises EncodingError."""
        layout = FieldLayout(
            name="active", type="boolean", offset=0, bits=1, constraints={}
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value("true", layout)

        assert exc_info.value.field_name == "active"
        assert "boolean" in str(exc_info.value).lower()
        assert "str" in str(exc_info.value)

    def test_integer_valid_in_range(self):
        """Integer field with value in range passes validation."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        validate_field_value(50, layout)  # Should not raise

    def test_integer_valid_at_min(self):
        """Integer field at minimum value passes validation."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        validate_field_value(0, layout)  # Should not raise

    def test_integer_valid_at_max(self):
        """Integer field at maximum value passes validation."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        validate_field_value(100, layout)  # Should not raise

    def test_integer_below_min(self):
        """Integer field below minimum raises EncodingError."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value(-1, layout)

        assert exc_info.value.field_name == "age"
        assert "-1" in str(exc_info.value)
        assert "0" in str(exc_info.value)
        assert "minimum" in str(exc_info.value).lower()

    def test_integer_above_max(self):
        """Integer field above maximum raises EncodingError."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value(101, layout)

        assert exc_info.value.field_name == "age"
        assert "101" in str(exc_info.value)
        assert "100" in str(exc_info.value)
        assert "maximum" in str(exc_info.value).lower()

    def test_integer_invalid_type(self):
        """Integer field with non-int value raises EncodingError."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value("42", layout)

        assert exc_info.value.field_name == "age"
        assert "integer" in str(exc_info.value).lower()

    def test_enum_valid_value(self):
        """Enum field with valid value passes validation."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["pending", "active", "done"]},
        )
        validate_field_value("active", layout)  # Should not raise

    def test_enum_invalid_value(self):
        """Enum field with invalid value raises EncodingError."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["pending", "active", "done"]},
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value("cancelled", layout)

        assert exc_info.value.field_name == "status"
        assert "cancelled" in str(exc_info.value)
        assert "pending" in str(exc_info.value)
        assert "active" in str(exc_info.value)
        assert "done" in str(exc_info.value)

    def test_nullable_field_with_none(self):
        """Nullable field with None value passes validation."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=8,
            constraints={"min": 0, "max": 100},
            nullable=True,
        )
        validate_field_value(None, layout)  # Should not raise

    def test_non_nullable_field_with_none(self):
        """Non-nullable field with None value raises EncodingError."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
            nullable=False,
        )
        with pytest.raises(EncodingError) as exc_info:
            validate_field_value(None, layout)

        assert exc_info.value.field_name == "age"
        assert "null" in str(exc_info.value).lower() or "none" in str(
            exc_info.value
        ).lower()


class TestValidateData:
    """Test validate_data function for complete data dict validation."""

    def test_all_required_fields_present_and_valid(self):
        """Data dict with all required fields passes validation."""
        layouts = [
            FieldLayout(
                name="active", type="boolean", offset=0, bits=1, constraints={}
            ),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 100},
            ),
        ]
        data = {"active": True, "age": 25}
        validate_data(data, layouts)  # Should not raise

    def test_missing_required_field(self):
        """Data dict missing required field raises EncodingError."""
        layouts = [
            FieldLayout(
                name="active", type="boolean", offset=0, bits=1, constraints={}
            ),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 100},
            ),
        ]
        data = {"active": True}  # Missing 'age'

        with pytest.raises(EncodingError) as exc_info:
            validate_data(data, layouts)

        assert "age" in str(exc_info.value)
        assert "missing" in str(exc_info.value).lower() or "required" in str(
            exc_info.value
        ).lower()

    def test_multiple_missing_required_fields(self):
        """Data dict missing multiple required fields raises EncodingError."""
        layouts = [
            FieldLayout(
                name="active", type="boolean", offset=0, bits=1, constraints={}
            ),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=7,
                constraints={"min": 0, "max": 100},
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=8,
                bits=2,
                constraints={"values": ["pending", "active", "done"]},
            ),
        ]
        data = {"active": True}  # Missing 'age' and 'status'

        with pytest.raises(EncodingError) as exc_info:
            validate_data(data, layouts)

        error_msg = str(exc_info.value)
        # Should mention both missing fields
        assert "age" in error_msg or "status" in error_msg

    def test_nullable_field_can_be_omitted(self):
        """Nullable fields can be omitted from data dict."""
        layouts = [
            FieldLayout(
                name="active", type="boolean", offset=0, bits=1, constraints={}
            ),
            FieldLayout(
                name="age",
                type="integer",
                offset=1,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
        ]
        data = {"active": True}  # 'age' is nullable so can be omitted
        validate_data(data, layouts)  # Should not raise

    def test_field_value_fails_validation(self):
        """Field value that fails validation raises EncodingError."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=7,
                constraints={"min": 0, "max": 100},
            ),
        ]
        data = {"age": 150}  # Exceeds max

        with pytest.raises(EncodingError) as exc_info:
            validate_data(data, layouts)

        assert exc_info.value.field_name == "age"
        assert "150" in str(exc_info.value)
        assert "maximum" in str(exc_info.value).lower()

    def test_extra_fields_allowed(self):
        """Extra fields in data dict are allowed (ignored)."""
        layouts = [
            FieldLayout(
                name="active", type="boolean", offset=0, bits=1, constraints={}
            ),
        ]
        data = {"active": True, "extra_field": "ignored"}
        validate_data(data, layouts)  # Should not raise

    def test_empty_data_with_all_nullable_fields(self):
        """Empty data dict passes when all fields are nullable."""
        layouts = [
            FieldLayout(
                name="age",
                type="integer",
                offset=0,
                bits=8,
                constraints={"min": 0, "max": 100},
                nullable=True,
            ),
            FieldLayout(
                name="active",
                type="boolean",
                offset=8,
                bits=2,
                constraints={},
                nullable=True,
            ),
        ]
        data = {}
        validate_data(data, layouts)  # Should not raise

    def test_empty_layouts_with_empty_data(self):
        """Empty layouts with empty data passes validation."""
        layouts = []
        data = {}
        validate_data(data, layouts)  # Should not raise
