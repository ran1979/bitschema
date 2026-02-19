"""Shared fixtures for BitSchema tests.

This module contains pytest configuration and reusable test fixtures
that are available to all test modules in the BitSchema test suite.

Includes Hypothesis composite strategies for generating test data.
"""

import pytest
from hypothesis import strategies as st


# Shared fixtures for BitSchema tests


# Hypothesis composite strategies for property-based testing


@st.composite
def bounded_integer_field(draw, min_val=None, max_val=None):
    """Generate bounded integer field definition with valid constraints.

    Args:
        draw: Hypothesis draw function
        min_val: Optional minimum value (will be generated if None)
        max_val: Optional maximum value (will be generated if None)

    Returns:
        Dict with type, min, max, and nullable keys
    """
    if min_val is None:
        min_val = draw(st.integers(min_value=-10000, max_value=10000))
    if max_val is None:
        max_val = draw(st.integers(min_value=min_val, max_value=min_val + 1000))

    return {
        "type": "integer",
        "min": min_val,
        "max": max_val,
        "nullable": draw(st.booleans())
    }


@st.composite
def enum_field(draw, num_values=None):
    """Generate enum field definition with valid values.

    Args:
        draw: Hypothesis draw function
        num_values: Optional number of enum values (will be generated if None)

    Returns:
        Dict with type, values, and nullable keys
    """
    if num_values is None:
        num_values = draw(st.integers(min_value=1, max_value=20))

    values = [f"value_{i}" for i in range(num_values)]

    return {
        "type": "enum",
        "values": values,
        "nullable": draw(st.booleans())
    }


@st.composite
def boolean_field(draw):
    """Generate boolean field definition.

    Args:
        draw: Hypothesis draw function

    Returns:
        Dict with type and nullable keys
    """
    return {
        "type": "boolean",
        "nullable": draw(st.booleans())
    }


@st.composite
def multi_field_schema(draw, num_fields=None, max_total_bits=64):
    """Generate schema with multiple fields that fit in specified bit limit.

    Args:
        draw: Hypothesis draw function
        num_fields: Optional number of fields (will be generated if None)
        max_total_bits: Maximum total bits for all fields (default 64)

    Returns:
        List of field dicts with name and field definition
    """
    if num_fields is None:
        num_fields = draw(st.integers(min_value=1, max_value=8))

    fields = []
    total_bits = 0

    for i in range(num_fields):
        # Calculate remaining bits
        remaining_bits = max_total_bits - total_bits

        if remaining_bits <= 0:
            break

        # Choose field type
        field_type = draw(st.sampled_from(["boolean", "integer", "enum"]))

        if field_type == "boolean":
            nullable = draw(st.booleans())
            field_bits = 2 if nullable else 1

            if field_bits <= remaining_bits:
                fields.append({
                    "name": f"field_{i}",
                    "type": "boolean",
                    "nullable": nullable
                })
                total_bits += field_bits

        elif field_type == "integer":
            nullable = draw(st.booleans())
            # Choose a reasonable bit count that fits
            max_bits = min(remaining_bits - (1 if nullable else 0), 16)

            if max_bits <= 0:
                continue

            bits = draw(st.integers(min_value=1, max_value=max_bits))
            max_value = (2 ** bits) - 1
            min_value = draw(st.integers(min_value=0, max_value=max_value // 2))

            field_bits = bits + (1 if nullable else 0)

            if field_bits <= remaining_bits:
                fields.append({
                    "name": f"field_{i}",
                    "type": "integer",
                    "min": min_value,
                    "max": min_value + max_value,
                    "nullable": nullable
                })
                total_bits += field_bits

        else:  # enum
            nullable = draw(st.booleans())
            # Choose number of values that fit in remaining bits
            max_bits = min(remaining_bits - (1 if nullable else 0), 8)

            if max_bits <= 0:
                continue

            num_values = draw(st.integers(min_value=1, max_value=2 ** max_bits))
            values = [f"value_{j}" for j in range(num_values)]

            if num_values == 1:
                bits = 0
            else:
                bits = (num_values - 1).bit_length()

            field_bits = bits + (1 if nullable else 0)

            if field_bits <= remaining_bits:
                fields.append({
                    "name": f"field_{i}",
                    "type": "enum",
                    "values": values,
                    "nullable": nullable
                })
                total_bits += field_bits

    return fields
