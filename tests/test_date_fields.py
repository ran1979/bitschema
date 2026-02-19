"""TDD tests for date field support.

Tests date field functionality including:
- Schema validation (min_date < max_date, valid resolution)
- Bit calculation for different resolutions (day, hour, minute, second)
- Date encoding (date → offset integer)
- Date decoding (offset integer → date)
- Round-trip correctness (encode → decode returns original)
- All resolution types
- Nullable date fields with presence bits
- Boundary date edge cases
"""

from datetime import datetime, date, timedelta
import pytest

from bitschema.models import BitSchema, DateFieldDefinition
from bitschema.layout import compute_bit_layout
from bitschema.encoder import encode
from bitschema.decoder import decode
from bitschema.errors import SchemaError


class TestDateFieldSchemaValidation:
    """Tests for date field schema validation."""

    def test_valid_date_field_definition(self):
        """Date field with valid parameters should validate."""
        field = DateFieldDefinition(
            type="date",
            resolution="day",
            min_date="2020-01-01",
            max_date="2030-12-31",
            nullable=False
        )
        assert field.type == "date"
        assert field.resolution == "day"
        assert field.min_date == "2020-01-01"
        assert field.max_date == "2030-12-31"
        assert field.nullable is False

    def test_min_date_must_be_before_max_date(self):
        """min_date >= max_date should raise ValidationError."""
        with pytest.raises(ValueError, match="min_date must be before max_date"):
            DateFieldDefinition(
                type="date",
                resolution="day",
                min_date="2030-12-31",
                max_date="2020-01-01"
            )

    def test_equal_min_max_date_raises_error(self):
        """min_date == max_date should raise ValidationError."""
        with pytest.raises(ValueError, match="min_date must be before max_date"):
            DateFieldDefinition(
                type="date",
                resolution="day",
                min_date="2025-01-01",
                max_date="2025-01-01"
            )

    def test_invalid_iso_date_format(self):
        """Invalid ISO 8601 date should raise ValidationError."""
        with pytest.raises(ValueError, match="Invalid ISO 8601 date"):
            DateFieldDefinition(
                type="date",
                resolution="day",
                min_date="not-a-date",
                max_date="2030-12-31"
            )

    def test_resolution_must_be_valid(self):
        """Resolution must be one of: day, hour, minute, second."""
        with pytest.raises(ValueError):
            DateFieldDefinition(
                type="date",
                resolution="millisecond",  # Invalid
                min_date="2020-01-01",
                max_date="2030-12-31"
            )


class TestDateFieldBitCalculation:
    """Tests for date field bit calculation."""

    def test_day_resolution_bit_calculation(self):
        """Day resolution should calculate bits based on total days."""
        fields = [
            {
                "name": "date_field",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",  # 366 days (leap year)
                "nullable": False
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)

        # 366 days - 1 = 365, bit_length(365) = 9 bits
        assert layouts[0].bits == 9
        assert total_bits == 9

    def test_hour_resolution_bit_calculation(self):
        """Hour resolution should calculate bits based on total hours."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "hour",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-02T00:00:00",  # 24 hours
                "nullable": False
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)

        # 24 hours - 1 = 23, bit_length(23) = 5 bits
        assert layouts[0].bits == 5
        assert total_bits == 5

    def test_minute_resolution_bit_calculation(self):
        """Minute resolution should calculate bits based on total minutes."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "minute",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-01T01:00:00",  # 60 minutes
                "nullable": False
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)

        # 60 minutes - 1 = 59, bit_length(59) = 6 bits
        assert layouts[0].bits == 6
        assert total_bits == 6

    def test_second_resolution_bit_calculation(self):
        """Second resolution should calculate bits based on total seconds."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "second",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-01T00:01:00",  # 60 seconds
                "nullable": False
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)

        # 60 seconds - 1 = 59, bit_length(59) = 6 bits
        assert layouts[0].bits == 6
        assert total_bits == 6


class TestDateFieldEncoding:
    """Tests for date field encoding."""

    def test_encode_day_resolution(self):
        """Encoding date with day resolution should produce correct offset."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # January 10th is 9 days after January 1st
        data = {"event_date": date(2020, 1, 10)}
        encoded = encode(data, layouts)

        # Should encode to offset of 9 days
        assert encoded == 9

    def test_encode_hour_resolution(self):
        """Encoding datetime with hour resolution should produce correct offset."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "hour",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-02T00:00:00",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # 5 hours after min_date
        data = {"timestamp": datetime(2025, 1, 1, 5, 0, 0)}
        encoded = encode(data, layouts)

        assert encoded == 5

    def test_encode_accepts_iso_string(self):
        """Encoding should accept ISO 8601 string format."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Should accept ISO string
        data = {"event_date": "2020-01-10"}
        encoded = encode(data, layouts)

        assert encoded == 9


class TestDateFieldDecoding:
    """Tests for date field decoding."""

    def test_decode_day_resolution(self):
        """Decoding offset with day resolution should return correct date."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Offset of 9 days
        encoded = 9
        decoded = decode(encoded, layouts)

        assert decoded["event_date"] == date(2020, 1, 10)

    def test_decode_hour_resolution(self):
        """Decoding offset with hour resolution should return correct datetime."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "hour",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-02T00:00:00",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Offset of 5 hours
        encoded = 5
        decoded = decode(encoded, layouts)

        assert decoded["timestamp"] == datetime(2025, 1, 1, 5, 0, 0)

    def test_decode_minute_resolution(self):
        """Decoding offset with minute resolution should return correct datetime."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "minute",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-01T02:00:00",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Offset of 45 minutes
        encoded = 45
        decoded = decode(encoded, layouts)

        assert decoded["timestamp"] == datetime(2025, 1, 1, 0, 45, 0)

    def test_decode_second_resolution(self):
        """Decoding offset with second resolution should return correct datetime."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "second",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-01-01T01:00:00",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Offset of 90 seconds
        encoded = 90
        decoded = decode(encoded, layouts)

        assert decoded["timestamp"] == datetime(2025, 1, 1, 0, 1, 30)


class TestDateFieldRoundTrip:
    """Tests for date field round-trip correctness."""

    def test_roundtrip_day_resolution(self):
        """Encode then decode should return original date (day resolution)."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        original_date = date(2020, 6, 15)
        data = {"event_date": original_date}

        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        assert decoded["event_date"] == original_date

    def test_roundtrip_hour_resolution(self):
        """Encode then decode should return original datetime (hour resolution)."""
        fields = [
            {
                "name": "timestamp",
                "type": "date",
                "resolution": "hour",
                "min_date": "2025-01-01T00:00:00",
                "max_date": "2025-12-31T23:00:00",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        original_datetime = datetime(2025, 6, 15, 14, 0, 0)
        data = {"timestamp": original_datetime}

        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        assert decoded["timestamp"] == original_datetime

    def test_roundtrip_all_resolutions(self):
        """Test round-trip for all resolution types."""
        test_cases = [
            ("day", "2020-01-01", "2020-12-31", date(2020, 6, 15)),
            ("hour", "2025-01-01T00:00:00", "2025-01-31T23:00:00", datetime(2025, 1, 15, 12, 0, 0)),
            ("minute", "2025-01-01T00:00:00", "2025-01-02T00:00:00", datetime(2025, 1, 1, 12, 30, 0)),
            ("second", "2025-01-01T00:00:00", "2025-01-01T06:00:00", datetime(2025, 1, 1, 3, 15, 45)),
        ]

        for resolution, min_date, max_date, test_value in test_cases:
            fields = [
                {
                    "name": "timestamp",
                    "type": "date",
                    "resolution": resolution,
                    "min_date": min_date,
                    "max_date": max_date,
                    "nullable": False
                }
            ]
            layouts, _ = compute_bit_layout(fields)

            data = {"timestamp": test_value}
            encoded = encode(data, layouts)
            decoded = decode(encoded, layouts)

            assert decoded["timestamp"] == test_value, f"Round-trip failed for resolution={resolution}"


class TestDateFieldNullable:
    """Tests for nullable date fields."""

    def test_nullable_date_field_adds_presence_bit(self):
        """Nullable date field should add 1 bit for presence."""
        fields = [
            {
                "name": "optional_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-01-31",
                "nullable": True
            }
        ]
        layouts, total_bits = compute_bit_layout(fields)

        # 31 days - 1 = 30, bit_length(30) = 5 bits + 1 presence bit = 6 bits
        assert layouts[0].bits == 6
        assert layouts[0].nullable is True

    def test_encode_nullable_date_none(self):
        """Encoding None for nullable date should set presence bit to 0."""
        fields = [
            {
                "name": "optional_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-01-31",
                "nullable": True
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"optional_date": None}
        encoded = encode(data, layouts)

        # Presence bit should be 0
        assert encoded == 0

    def test_decode_nullable_date_none(self):
        """Decoding with presence bit 0 should return None."""
        fields = [
            {
                "name": "optional_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-01-31",
                "nullable": True
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        encoded = 0  # Presence bit = 0
        decoded = decode(encoded, layouts)

        assert decoded["optional_date"] is None

    def test_roundtrip_nullable_date_with_value(self):
        """Round-trip for nullable date with actual value."""
        fields = [
            {
                "name": "optional_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": True
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        original_date = date(2020, 6, 15)
        data = {"optional_date": original_date}

        encoded = encode(data, layouts)
        decoded = decode(encoded, layouts)

        assert decoded["optional_date"] == original_date


class TestDateFieldBoundaries:
    """Tests for date field boundary conditions."""

    def test_encode_min_date_boundary(self):
        """Encoding min_date should produce offset 0."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"event_date": date(2020, 1, 1)}
        encoded = encode(data, layouts)

        assert encoded == 0

    def test_encode_max_date_boundary(self):
        """Encoding max_date should produce maximum offset."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-01-31",  # 31 days total
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        data = {"event_date": date(2020, 1, 31)}
        encoded = encode(data, layouts)

        # max_date - min_date = 30 days
        assert encoded == 30

    def test_roundtrip_boundary_dates(self):
        """Round-trip test for min_date and max_date boundaries."""
        fields = [
            {
                "name": "event_date",
                "type": "date",
                "resolution": "day",
                "min_date": "2020-01-01",
                "max_date": "2020-12-31",
                "nullable": False
            }
        ]
        layouts, _ = compute_bit_layout(fields)

        # Test min_date boundary
        min_data = {"event_date": date(2020, 1, 1)}
        min_encoded = encode(min_data, layouts)
        min_decoded = decode(min_encoded, layouts)
        assert min_decoded["event_date"] == date(2020, 1, 1)

        # Test max_date boundary
        max_data = {"event_date": date(2020, 12, 31)}
        max_encoded = encode(max_data, layouts)
        max_decoded = decode(max_encoded, layouts)
        assert max_decoded["event_date"] == date(2020, 12, 31)
