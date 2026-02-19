"""Bit layout visualization for BitSchema.

Generates human-readable tables showing field positions, types, and constraints.
Supports both ASCII grid format (for console/logs) and markdown format (for docs).
"""

from tabulate import tabulate

from .layout import FieldLayout


def format_bit_range(layout: FieldLayout) -> str:
    """Format bit range as 'offset:end'.

    Args:
        layout: Field layout with offset and bits

    Returns:
        Bit range string in format "offset:end" (e.g., "0:7" for 8 bits at offset 0)

    Examples:
        >>> layout = FieldLayout("age", "integer", 0, 8, {"min": 0, "max": 255}, False)
        >>> format_bit_range(layout)
        '0:7'
        >>> layout = FieldLayout("active", "boolean", 0, 1, {}, False)
        >>> format_bit_range(layout)
        '0:0'
    """
    end_bit = layout.offset + layout.bits - 1
    return f"{layout.offset}:{end_bit}"


def format_constraints(layout: FieldLayout) -> str:
    """Format constraints as human-friendly string.

    Args:
        layout: Field layout with type, constraints, and nullable flag

    Returns:
        Constraint string formatted based on field type:
        - Boolean: "-"
        - Integer: "[min..max]"
        - Enum: "N values"
        - Nullable: adds " (nullable)" suffix

    Examples:
        >>> layout = FieldLayout("active", "boolean", 0, 1, {}, False)
        >>> format_constraints(layout)
        '-'
        >>> layout = FieldLayout("age", "integer", 0, 7, {"min": 0, "max": 100}, False)
        >>> format_constraints(layout)
        '[0..100]'
        >>> layout = FieldLayout("status", "enum", 0, 2, {"values": ["a", "b", "c"]}, False)
        >>> format_constraints(layout)
        '3 values'
        >>> layout = FieldLayout("age", "integer", 0, 8, {"min": 0, "max": 100}, True)
        >>> format_constraints(layout)
        '[0..100] (nullable)'
    """
    if layout.type == "boolean":
        constraint_str = "-"
    elif layout.type == "integer":
        min_val = layout.constraints["min"]
        max_val = layout.constraints["max"]
        constraint_str = f"[{min_val}..{max_val}]"
    elif layout.type == "enum":
        value_count = len(layout.constraints["values"])
        constraint_str = f"{value_count} values"
    else:
        constraint_str = "-"

    # Add nullable suffix if applicable
    if layout.nullable:
        constraint_str += " (nullable)"

    return constraint_str


def visualize_bit_layout_ascii(layouts: list[FieldLayout]) -> str:
    """Generate ASCII grid table showing bit layout.

    Args:
        layouts: List of field layouts in declaration order

    Returns:
        ASCII grid table with borders, headers, and field details

    Example output:
        +--------+------+-----------+------+-------------+
        | Field  | Type | Bit Range | Bits | Constraints |
        +========+======+===========+======+=============+
        | active | bool | 0:0       | 1    | -           |
        | age    | int  | 1:7       | 7    | [0..100]    |
        +--------+------+-----------+------+-------------+
    """
    headers = ["Field", "Type", "Bit Range", "Bits", "Constraints"]
    table_data = []

    for layout in layouts:
        row = [
            layout.name,
            layout.type,
            format_bit_range(layout),
            layout.bits,
            format_constraints(layout),
        ]
        table_data.append(row)

    return tabulate(table_data, headers=headers, tablefmt="grid")


def visualize_bit_layout_markdown(layouts: list[FieldLayout]) -> str:
    """Generate markdown table showing bit layout.

    Args:
        layouts: List of field layouts in declaration order

    Returns:
        Valid GitHub-flavored markdown table with field details

    Example output:
        | Field  | Type | Bit Range | Bits | Constraints |
        |--------|------|-----------|------|-------------|
        | active | bool | 0:0       | 1    | -           |
        | age    | int  | 1:7       | 7    | [0..100]    |
    """
    headers = ["Field", "Type", "Bit Range", "Bits", "Constraints"]
    table_data = []

    for layout in layouts:
        row = [
            layout.name,
            layout.type,
            format_bit_range(layout),
            layout.bits,
            format_constraints(layout),
        ]
        table_data.append(row)

    return tabulate(table_data, headers=headers, tablefmt="github")


def visualize_bit_layout(
    layouts: list[FieldLayout], format: str = "ascii"
) -> str:
    """Generate bit layout visualization in specified format.

    Args:
        layouts: List of field layouts in declaration order
        format: Output format - "ascii" (default) or "markdown"

    Returns:
        Formatted table string

    Raises:
        ValueError: If format is not "ascii" or "markdown"

    Examples:
        >>> layouts = [FieldLayout("active", "boolean", 0, 1, {}, False)]
        >>> table = visualize_bit_layout(layouts, format="ascii")
        >>> "+" in table  # ASCII grid has borders
        True
        >>> table = visualize_bit_layout(layouts, format="markdown")
        >>> "---" in table  # Markdown has separator
        True
    """
    if format == "ascii":
        return visualize_bit_layout_ascii(layouts)
    elif format == "markdown":
        return visualize_bit_layout_markdown(layouts)
    else:
        raise ValueError(f"Unknown format: {format}. Use 'ascii' or 'markdown'.")
