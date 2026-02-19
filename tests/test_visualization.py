"""Tests for bit layout visualization."""

import pytest

from bitschema.layout import FieldLayout
from bitschema.visualization import (
    format_bit_range,
    format_constraints,
    visualize_bit_layout,
    visualize_bit_layout_ascii,
    visualize_bit_layout_markdown,
)


class TestFormatBitRange:
    """Tests for bit range formatting."""

    def test_single_bit(self):
        """Single bit field shows offset:offset format."""
        layout = FieldLayout(
            name="active",
            type="boolean",
            offset=0,
            bits=1,
            constraints={},
            nullable=False,
        )
        assert format_bit_range(layout) == "0:0"

    def test_multiple_bits(self):
        """Multiple bit field shows offset:end format."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=1,
            bits=7,
            constraints={"min": 0, "max": 127},
            nullable=False,
        )
        assert format_bit_range(layout) == "1:7"

    def test_enum_bits(self):
        """Enum field shows correct bit range."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=8,
            bits=2,
            constraints={"values": ["pending", "active", "done"]},
            nullable=False,
        )
        assert format_bit_range(layout) == "8:9"


class TestFormatConstraints:
    """Tests for constraint formatting."""

    def test_boolean_no_constraints(self):
        """Boolean field shows dash for constraints."""
        layout = FieldLayout(
            name="active",
            type="boolean",
            offset=0,
            bits=1,
            constraints={},
            nullable=False,
        )
        assert format_constraints(layout) == "-"

    def test_integer_range(self):
        """Integer field shows [min..max] format."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=7,
            constraints={"min": 0, "max": 100},
            nullable=False,
        )
        assert format_constraints(layout) == "[0..100]"

    def test_integer_negative_range(self):
        """Integer field with negative values shows correct range."""
        layout = FieldLayout(
            name="temperature",
            type="integer",
            offset=0,
            bits=8,
            constraints={"min": -50, "max": 50},
            nullable=False,
        )
        assert format_constraints(layout) == "[-50..50]"

    def test_enum_value_count(self):
        """Enum field shows 'N values' format."""
        layout = FieldLayout(
            name="status",
            type="enum",
            offset=0,
            bits=2,
            constraints={"values": ["pending", "active", "done"]},
            nullable=False,
        )
        assert format_constraints(layout) == "3 values"

    def test_nullable_suffix(self):
        """Nullable field adds (nullable) suffix."""
        layout = FieldLayout(
            name="age",
            type="integer",
            offset=0,
            bits=8,
            constraints={"min": 0, "max": 100},
            nullable=True,
        )
        assert format_constraints(layout) == "[0..100] (nullable)"

    def test_nullable_boolean(self):
        """Nullable boolean adds suffix to dash."""
        layout = FieldLayout(
            name="active",
            type="boolean",
            offset=0,
            bits=2,
            constraints={},
            nullable=True,
        )
        assert format_constraints(layout) == "- (nullable)"


class TestVisualizeAsciiFormat:
    """Tests for ASCII table visualization."""

    def test_single_field_ascii(self):
        """Single field generates ASCII grid table."""
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
        result = visualize_bit_layout_ascii(layouts)

        # Check table structure
        assert "Field" in result
        assert "Type" in result
        assert "Bit Range" in result
        assert "Bits" in result
        assert "Constraints" in result

        # Check data
        assert "active" in result
        assert "boolean" in result
        assert "0:0" in result
        assert "1" in result
        assert "-" in result

        # Check ASCII grid borders
        assert "+" in result
        assert "|" in result
        assert "=" in result

    def test_multi_field_ascii(self):
        """Multiple fields show all in order."""
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
                name="priority",
                type="integer",
                offset=1,
                bits=3,
                constraints={"min": 0, "max": 7},
                nullable=False,
            ),
            FieldLayout(
                name="status",
                type="enum",
                offset=4,
                bits=2,
                constraints={"values": ["pending", "active", "done"]},
                nullable=False,
            ),
        ]
        result = visualize_bit_layout_ascii(layouts)

        # Check all fields present
        assert "active" in result
        assert "priority" in result
        assert "status" in result

        # Check bit ranges
        assert "0:0" in result
        assert "1:3" in result
        assert "4:5" in result

        # Check constraints
        assert "[0..7]" in result
        assert "3 values" in result


class TestVisualizeMarkdownFormat:
    """Tests for markdown table visualization."""

    def test_single_field_markdown(self):
        """Single field generates valid markdown table."""
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
        result = visualize_bit_layout_markdown(layouts)

        # Check markdown table structure
        assert "|" in result
        assert "Field" in result
        assert "Type" in result
        assert "Bit Range" in result

        # Check data
        assert "active" in result
        assert "boolean" in result
        assert "0:0" in result

        # Check markdown separator (should have dashes)
        assert "---" in result

    def test_multi_field_markdown(self):
        """Multiple fields show all in markdown format."""
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
                constraints={"min": 0, "max": 100},
                nullable=False,
            ),
        ]
        result = visualize_bit_layout_markdown(layouts)

        # Check both fields
        assert "active" in result
        assert "age" in result

        # Check types
        assert "boolean" in result
        assert "integer" in result

        # Check constraints
        assert "[0..100]" in result


class TestVisualizeDispatcher:
    """Tests for format dispatcher function."""

    def test_ascii_format(self):
        """Format='ascii' returns ASCII grid table."""
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
        result = visualize_bit_layout(layouts, format="ascii")

        # Should have grid borders
        assert "+" in result
        assert "=" in result

    def test_markdown_format(self):
        """Format='markdown' returns markdown table."""
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
        result = visualize_bit_layout(layouts, format="markdown")

        # Should have markdown separators
        assert "---" in result
        # Should NOT have grid borders
        assert "+" not in result

    def test_default_format(self):
        """Default format is ascii."""
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
        result = visualize_bit_layout(layouts)

        # Default should be ASCII
        assert "+" in result
        assert "=" in result

    def test_invalid_format(self):
        """Invalid format raises ValueError."""
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
        with pytest.raises(ValueError, match="Unknown format"):
            visualize_bit_layout(layouts, format="invalid")
