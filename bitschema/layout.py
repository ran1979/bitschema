"""Bit layout computation for BitSchema fields.

Computes deterministic bit offsets and widths for fields, ensuring total
bit count stays within 64-bit limit. Core mathematical correctness guarantee.
"""

from typing import NamedTuple
from datetime import datetime

from .errors import SchemaError


class FieldLayout(NamedTuple):
    """Layout information for a single field.

    Attributes:
        name: Field name
        type: Field type (boolean, integer, enum)
        offset: Starting bit position (0-indexed from LSB)
        bits: Number of bits allocated for this field
        constraints: Type-specific constraints (min/max for integer, values for enum)
        nullable: Whether field can be null (presence bit included in bits count)

    Example:
        FieldLayout(name="age", type="integer", offset=0, bits=7,
                    constraints={"min": 0, "max": 100}, nullable=False)
    """

    name: str
    type: str
    offset: int
    bits: int
    constraints: dict
    nullable: bool = False


def compute_field_bits(field: dict) -> int:
    """Compute minimum required bits for a field.

    Uses int.bit_length() for mathematical correctness, avoiding float precision
    issues from math.log2().

    Args:
        field: Field definition dict with type and constraints

    Returns:
        Minimum bits required to represent all possible field values

    Algorithm:
        - Boolean: 1 bit (0 or 1)
        - Integer: (max - min).bit_length() - represents range size
        - Enum: (len(values) - 1).bit_length() - represents max index
          Special case: single-value enum requires 0 bits (constant)

    Examples:
        Boolean: 1 bit
        Integer [0, 255]: (255 - 0).bit_length() = 8 bits
        Integer [-128, 127]: (127 - (-128)).bit_length() = 8 bits
        Enum ["a", "b", "c"]: (3 - 1).bit_length() = 2 bits
        Enum ["only"]: (1 - 1).bit_length() = 0 bits
    """
    field_type = field["type"]

    if field_type == "boolean":
        return 1

    elif field_type == "integer":
        min_value = field["min"]
        max_value = field["max"]
        # Range size: number of distinct values
        range_size = max_value - min_value
        return range_size.bit_length()

    elif field_type == "enum":
        values = field["values"]
        if len(values) == 1:
            # Single value is constant, needs 0 bits
            return 0
        # Maximum index requires log2(n) bits
        max_index = len(values) - 1
        return max_index.bit_length()

    elif field_type == "date":
        min_dt = datetime.fromisoformat(field["min_date"])
        max_dt = datetime.fromisoformat(field["max_date"])
        resolution = field["resolution"]

        # Calculate total units based on resolution
        if resolution == "day":
            total_units = (max_dt - min_dt).days
        elif resolution == "hour":
            total_units = int((max_dt - min_dt).total_seconds() / 3600)
        elif resolution == "minute":
            total_units = int((max_dt - min_dt).total_seconds() / 60)
        elif resolution == "second":
            total_units = int((max_dt - min_dt).total_seconds())
        else:
            raise SchemaError(f"Invalid date resolution: {resolution}")

        # Return bits needed to represent range
        return (total_units - 1).bit_length() if total_units > 0 else 0

    else:
        raise SchemaError(f"Unknown field type: {field_type}")


def compute_bit_layout(fields: list[dict]) -> tuple[list[FieldLayout], int]:
    """Compute deterministic bit layout for schema fields.

    Assigns sequential bit offsets starting from 0, preserving field order.
    Validates total bit count stays within 64-bit limit.

    Args:
        fields: List of field definition dicts

    Returns:
        Tuple of (layouts, total_bits):
            - layouts: List of FieldLayout for each field in order
            - total_bits: Total bits required for all fields

    Raises:
        SchemaError: If total bits exceed 64-bit limit, with detailed breakdown

    Algorithm:
        1. Initialize offset = 0
        2. For each field in declaration order:
           a. Compute required bits for value
           b. Add 1 bit if field is nullable (presence tracking)
           c. Create FieldLayout with current offset
           d. Increment offset by field bits
        3. Validate total <= 64 bits
        4. Return layouts and total

    Example:
        >>> fields = [
        ...     {"name": "active", "type": "boolean"},
        ...     {"name": "age", "type": "integer", "min": 0, "max": 127}
        ... ]
        >>> layouts, total = compute_bit_layout(fields)
        >>> layouts[0]
        FieldLayout(name='active', type='boolean', offset=0, bits=1, constraints={}, nullable=False)
        >>> layouts[1]
        FieldLayout(name='age', type='integer', offset=1, bits=7,
                    constraints={'min': 0, 'max': 127}, nullable=False)
        >>> total
        8
    """
    layouts = []
    offset = 0

    # Compute layout for each field in order
    for field in fields:
        # Compute required bits for value
        bits = compute_field_bits(field)

        # Check if field is nullable (default to False if not specified)
        nullable = field.get("nullable", False)

        # Add presence bit for nullable fields
        if nullable:
            bits += 1

        # Extract constraints based on type
        constraints = {}
        if field["type"] == "integer":
            constraints = {"min": field["min"], "max": field["max"]}
        elif field["type"] == "enum":
            constraints = {"values": field["values"]}
        elif field["type"] == "date":
            constraints = {
                "min_date": field["min_date"],
                "max_date": field["max_date"],
                "resolution": field["resolution"]
            }

        # Create layout with current offset
        layout = FieldLayout(
            name=field["name"],
            type=field["type"],
            offset=offset,
            bits=bits,
            constraints=constraints,
            nullable=nullable,
        )

        layouts.append(layout)
        offset += bits

    # Validate 64-bit limit
    total_bits = offset
    if total_bits > 64:
        # Create detailed breakdown for error message
        breakdown = ", ".join(f"{layout.name}={layout.bits}" for layout in layouts)
        raise SchemaError(
            f"Schema exceeds 64-bit limit: {total_bits} bits total. "
            f"Breakdown: {breakdown}"
        )

    return layouts, total_bits
