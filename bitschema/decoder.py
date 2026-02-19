"""Bit-unpacking decoder for BitSchema.

Transforms 64-bit integers back to Python dictionaries using field layouts.
Implements bit extraction, denormalization, and nullable field handling.
"""

from typing import Any
from datetime import datetime, timedelta

from .layout import FieldLayout


def denormalize_value(extracted: int, layout: FieldLayout) -> Any:
    """Denormalize extracted bits to semantic value.

    Converts unsigned bit representation back to typed Python value.

    Args:
        extracted: Unsigned integer extracted from encoded bits
        layout: Field layout with type and constraints

    Returns:
        Denormalized value in semantic type (bool, int, str)

    Algorithm:
        - Boolean: Convert 0/1 to False/True
        - Integer: Add min to convert unsigned to signed range
        - Enum: Index into values list to get string

    Examples:
        >>> layout = FieldLayout(name="active", type="boolean", offset=0, bits=1,
        ...                      constraints={}, nullable=False)
        >>> denormalize_value(1, layout)
        True

        >>> layout = FieldLayout(name="temp", type="integer", offset=0, bits=5,
        ...                      constraints={"min": -10, "max": 10}, nullable=False)
        >>> denormalize_value(5, layout)  # 5 - 10 = -5
        -5

        >>> layout = FieldLayout(name="status", type="enum", offset=0, bits=2,
        ...                      constraints={"values": ["idle", "active"]}, nullable=False)
        >>> denormalize_value(1, layout)
        'active'
    """
    if layout.type == "boolean":
        # Convert 0/1 to False/True
        return bool(extracted)

    elif layout.type == "integer":
        # Denormalize: add min to convert unsigned to signed
        min_value = layout.constraints.get("min", 0)
        return extracted + min_value

    elif layout.type == "enum":
        # Convert index to enum value
        values = layout.constraints["values"]
        return values[extracted]

    elif layout.type == "date":
        min_date_str = layout.constraints["min_date"]
        min_date = datetime.fromisoformat(min_date_str)
        resolution = layout.constraints["resolution"]

        # Calculate datetime by adding offset to min_date
        if resolution == "day":
            result = (min_date + timedelta(days=extracted)).date()
        elif resolution == "hour":
            result = min_date + timedelta(hours=extracted)
        elif resolution == "minute":
            result = min_date + timedelta(minutes=extracted)
        elif resolution == "second":
            result = min_date + timedelta(seconds=extracted)
        else:
            raise ValueError(f"Invalid date resolution: {resolution}")

        return result

    else:
        # Should never happen if layout is valid
        raise ValueError(f"Unknown field type: {layout.type}")


def decode(encoded: int, layouts: list[FieldLayout]) -> dict:
    """Decode 64-bit integer to dictionary using field layouts.

    Extracts bits at computed offsets and denormalizes to semantic values.
    Handles nullable fields by checking presence bits.

    Args:
        encoded: 64-bit integer with packed field data
        layouts: Field layouts in declaration order

    Returns:
        Dictionary mapping field names to decoded values

    Algorithm:
        1. Initialize empty result dict
        2. For each field in layout order:
           a. If nullable: check presence bit at offset
              - If presence = 0: set to None, skip value extraction
              - If presence = 1: extract value from offset+1
           b. If non-nullable: extract value from offset
           c. Create mask for field width
           d. Extract bits: (encoded >> offset) & mask
           e. Denormalize to semantic value
           f. Store in result dict with field name
        3. Return result dict

    Example:
        >>> layouts = [
        ...     FieldLayout(name="active", type="boolean", offset=0, bits=1,
        ...                 constraints={}, nullable=False),
        ...     FieldLayout(name="age", type="integer", offset=1, bits=7,
        ...                 constraints={"min": 0, "max": 127}, nullable=False)
        ... ]
        >>> encoded = 85  # 0b1010101
        >>> decode(encoded, layouts)
        {'active': True, 'age': 42}

    Nullable field example:
        >>> layouts = [
        ...     FieldLayout(name="optional", type="integer", offset=0, bits=8,
        ...                 constraints={"min": 0, "max": 127}, nullable=True)
        ... ]
        >>> decode(0, layouts)  # presence bit = 0
        {'optional': None}
        >>> decode(85, layouts)  # presence bit = 1, value = 42
        {'optional': 42}
    """
    result = {}

    for layout in layouts:
        if layout.nullable:
            # Nullable field: check presence bit first
            presence_offset = layout.offset
            presence = (encoded >> presence_offset) & 1

            if presence == 0:
                # Field is None
                result[layout.name] = None
            else:
                # Field has value: extract from offset+1
                value_offset = layout.offset + 1
                value_bits = layout.bits - 1  # Exclude presence bit

                # Create mask for value width
                mask = (1 << value_bits) - 1

                # Extract value bits
                extracted = (encoded >> value_offset) & mask

                # Denormalize and store
                result[layout.name] = denormalize_value(extracted, layout)
        else:
            # Non-nullable field: extract directly from offset
            # Create mask for field width
            mask = (1 << layout.bits) - 1

            # Extract bits at offset
            extracted = (encoded >> layout.offset) & mask

            # Denormalize to semantic value
            result[layout.name] = denormalize_value(extracted, layout)

    return result
