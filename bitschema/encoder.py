"""Bit-packing encoder for encoding data dict to 64-bit integer.

Implements LSB-first accumulator pattern with fail-fast validation.
Handles all field types (boolean, integer, enum) and nullable fields
with presence bit tracking.
"""

from typing import Any
from datetime import datetime, date

from .layout import FieldLayout
from .validator import validate_data


def normalize_value(value: Any, layout: FieldLayout) -> int:
    """Normalize field value to unsigned integer for bit packing.

    Converts semantic values (bool, signed int, enum string) to unsigned
    integer representation suitable for bitwise operations.

    Args:
        value: The semantic value to normalize
        layout: Field layout with type and constraints

    Returns:
        Unsigned integer representation of the value

    Normalization rules:
        - Boolean: True → 1, False → 0
        - Integer: value - min (convert signed to unsigned)
        - Enum: index of value in values list

    Examples:
        >>> layout = FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={})
        >>> normalize_value(True, layout)
        1

        >>> layout = FieldLayout(name="temp", type="integer", offset=0, bits=5,
        ...                      constraints={"min": -10, "max": 10})
        >>> normalize_value(-5, layout)
        5  # -5 - (-10) = 5

        >>> layout = FieldLayout(name="status", type="enum", offset=0, bits=2,
        ...                      constraints={"values": ["idle", "active", "done"]})
        >>> normalize_value("active", layout)
        1  # Index of "active" in list
    """
    if layout.type == "boolean":
        return 1 if value else 0

    elif layout.type == "integer":
        # Normalize to unsigned by subtracting min
        min_value = layout.constraints.get("min", 0)
        return value - min_value

    elif layout.type == "enum":
        # Convert to index in values list
        values = layout.constraints["values"]
        return values.index(value)

    elif layout.type == "date":
        min_date_str = layout.constraints["min_date"]
        min_date = datetime.fromisoformat(min_date_str)
        resolution = layout.constraints["resolution"]

        # Parse input value if it's a string
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        # Convert date to datetime for consistent handling
        elif isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())

        # Calculate offset based on resolution
        if resolution == "day":
            offset = (value - min_date).days
        elif resolution == "hour":
            offset = int((value - min_date).total_seconds() / 3600)
        elif resolution == "minute":
            offset = int((value - min_date).total_seconds() / 60)
        elif resolution == "second":
            offset = int((value - min_date).total_seconds())
        else:
            raise ValueError(f"Invalid date resolution: {resolution}")

        return offset

    else:
        raise ValueError(f"Unknown field type: {layout.type}")


def encode(data: dict[str, Any], layouts: list[FieldLayout]) -> int:
    """Encode Python dict to 64-bit integer using schema layouts.

    Implements LSB-first accumulator pattern:
    1. Validate data before any bit operations (fail-fast)
    2. For each field in layout order:
       - Handle nullable: check presence, pack presence bit + value bits
       - Normalize value to unsigned integer
       - Create bit mask for field width
       - Pack into accumulator using OR and left shift
    3. Return packed integer

    Args:
        data: Dictionary mapping field names to values
        layouts: List of field layouts in bit order

    Returns:
        64-bit integer with packed field values

    Raises:
        EncodingError: If validation fails (from validate_data)

    Algorithm:
        For non-nullable field at offset O with N bits:
            accumulator |= ((normalized_value & mask) << O)

        For nullable field at offset O with N value bits:
            if value is None:
                presence_bit = 0, skip N+1 bits
            else:
                presence_bit = 1 at offset O
                value_bits at offset O+1
            accumulator |= (presence_bit << O) | ((normalized_value & mask) << (O+1))

    Examples:
        >>> layouts = [
        ...     FieldLayout(name="active", type="boolean", offset=0, bits=1, constraints={}),
        ...     FieldLayout(name="age", type="integer", offset=1, bits=7,
        ...                 constraints={"min": 0, "max": 127}),
        ... ]
        >>> data = {"active": True, "age": 42}
        >>> encode(data, layouts)
        85  # 0b1010101 = 1 | (42 << 1)
    """
    # Validate data before any bit operations (fail-fast)
    validate_data(data, layouts)

    accumulator = 0

    for layout in layouts:
        # Get value from data dict
        value = data.get(layout.name)

        # Handle nullable fields
        if layout.nullable:
            if value is None:
                # Presence bit = 0 (default), skip all bits for this field
                # No operation needed - accumulator already has 0 bits
                continue
            else:
                # Presence bit = 1 at current offset
                accumulator |= 1 << layout.offset

                # Normalize and pack value bits at offset + 1
                normalized = normalize_value(value, layout)
                # Value bits count is total bits - 1 (for presence bit)
                value_bits = layout.bits - 1
                mask = (1 << value_bits) - 1 if value_bits > 0 else 0
                accumulator |= (normalized & mask) << (layout.offset + 1)
                continue

        # Non-nullable field: normalize and pack value
        normalized = normalize_value(value, layout)

        # Create mask for field width
        mask = (1 << layout.bits) - 1 if layout.bits > 0 else 0

        # Pack into accumulator at offset
        accumulator |= (normalized & mask) << layout.offset

    return accumulator
