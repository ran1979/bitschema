"""Dataclass code generation from BitSchema schemas.

Generates type-safe Python dataclass code with encode/decode methods
that match runtime encoder/decoder behavior exactly.
"""

import ast
import subprocess
import textwrap
from typing import Any

from .models import (
    BitSchema,
    BoolFieldDefinition,
    IntFieldDefinition,
    EnumFieldDefinition,
    DateFieldDefinition,
    BitmaskFieldDefinition,
    FieldDefinition,
)
from .layout import FieldLayout


def generate_field_type_hint(field_name: str, field_def: FieldDefinition) -> str:
    """Generate Python type hint for a field.

    Args:
        field_name: Name of the field
        field_def: Field definition with type and constraints

    Returns:
        Type hint string (e.g., "int", "bool", "str", "int | None")

    Examples:
        >>> field_def = BoolFieldDefinition(type="bool")
        >>> generate_field_type_hint("active", field_def)
        'bool'

        >>> field_def = IntFieldDefinition(type="int", bits=8, min=0, max=255, nullable=True)
        >>> generate_field_type_hint("age", field_def)
        'int | None'
    """
    # Map field type to Python type
    if isinstance(field_def, BoolFieldDefinition):
        type_hint = "bool"
    elif isinstance(field_def, IntFieldDefinition):
        type_hint = "int"
    elif isinstance(field_def, EnumFieldDefinition):
        type_hint = "str"
    elif isinstance(field_def, DateFieldDefinition):
        # day resolution returns date, others return datetime
        if field_def.resolution == "day":
            type_hint = "datetime.date"
        else:
            type_hint = "datetime.datetime"
    elif isinstance(field_def, BitmaskFieldDefinition):
        type_hint = "dict[str, bool]"
    else:
        raise ValueError(f"Unknown field type: {type(field_def)}")

    # Add None for nullable fields
    if field_def.nullable:
        type_hint = f"{type_hint} | None"

    return type_hint


def generate_field_definitions(schema: BitSchema) -> str:
    """Generate field definitions for dataclass.

    Args:
        schema: BitSchema with field definitions

    Returns:
        Field definitions as indented strings

    Example:
        >>> schema = BitSchema(
        ...     version="1",
        ...     name="Person",
        ...     fields={
        ...         "active": BoolFieldDefinition(type="bool"),
        ...         "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
        ...     }
        ... )
        >>> print(generate_field_definitions(schema))
        active: bool
        age: int
    """
    lines = []
    for field_name, field_def in schema.fields.items():
        type_hint = generate_field_type_hint(field_name, field_def)

        # Add default None for nullable fields
        if field_def.nullable:
            lines.append(f"{field_name}: {type_hint} = None")
        else:
            lines.append(f"{field_name}: {type_hint}")

    return "\n".join(lines)


def _generate_normalize_expression(field_name: str, field_def: FieldDefinition) -> str:
    """Generate normalization expression for a field value.

    Args:
        field_name: Name of the field
        field_def: Field definition with type and constraints

    Returns:
        Python expression string that normalizes the field value

    Examples:
        >>> _generate_normalize_expression("active", BoolFieldDefinition(type="bool"))
        '1 if self.active else 0'
    """
    if isinstance(field_def, BoolFieldDefinition):
        return f"1 if self.{field_name} else 0"
    elif isinstance(field_def, IntFieldDefinition):
        min_value = field_def.min if field_def.min is not None else 0
        if min_value != 0:
            return f"self.{field_name} - {min_value}"
        else:
            return f"self.{field_name}"
    elif isinstance(field_def, EnumFieldDefinition):
        values_repr = repr(field_def.values)
        return f"{values_repr}.index(self.{field_name})"
    elif isinstance(field_def, DateFieldDefinition):
        # Date normalization is more complex - handled inline in encode method
        return None  # Signal to use inline code block
    elif isinstance(field_def, BitmaskFieldDefinition):
        # Bitmask normalization is more complex - handled inline in encode method
        return None  # Signal to use inline code block
    else:
        raise ValueError(f"Unknown field type: {type(field_def)}")


def _generate_date_encoding_inline(lines: list[str], field_name: str, field_def: DateFieldDefinition, indent: str) -> None:
    """Generate inline date encoding logic."""
    min_date = field_def.min_date
    resolution = field_def.resolution

    lines.append(f'{indent}min_date = datetime.fromisoformat("{min_date}")')
    lines.append(f'{indent}value = self.{field_name}')
    lines.append(f'{indent}# Convert date to datetime for consistent handling')
    lines.append(f'{indent}if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):')
    lines.append(f'{indent}    value = datetime.datetime.combine(value, datetime.datetime.min.time())')

    if resolution == "day":
        lines.append(f'{indent}normalized = (value - min_date).days')
    elif resolution == "hour":
        lines.append(f'{indent}normalized = int((value - min_date).total_seconds() / 3600)')
    elif resolution == "minute":
        lines.append(f'{indent}normalized = int((value - min_date).total_seconds() / 60)')
    elif resolution == "second":
        lines.append(f'{indent}normalized = int((value - min_date).total_seconds())')


def _generate_bitmask_encoding_inline(lines: list[str], field_name: str, field_def: BitmaskFieldDefinition, indent: str) -> None:
    """Generate inline bitmask encoding logic."""
    flags_repr = repr(field_def.flags)

    lines.append(f'{indent}flags_def = {flags_repr}')
    lines.append(f'{indent}normalized = 0')
    lines.append(f'{indent}for flag_name, flag_position in flags_def.items():')
    lines.append(f'{indent}    if self.{field_name}.get(flag_name, False):')
    lines.append(f'{indent}        normalized |= (1 << flag_position)')


def generate_encode_method(schema: BitSchema, layouts: list[FieldLayout]) -> str:
    """Generate encode() method using LSB-first accumulator pattern.

    Args:
        schema: BitSchema with field definitions
        layouts: Field layouts with bit offsets and constraints

    Returns:
        Encode method source code

    Algorithm:
        Mirrors encoder.py logic:
        1. Initialize accumulator = 0
        2. For each field:
           - If nullable and None: skip (presence bit = 0)
           - If nullable and value: set presence bit, pack value at offset+1
           - If non-nullable: normalize and pack at offset
        3. Return accumulator
    """
    lines = []
    lines.append("def encode(self) -> int:")
    lines.append('    """Encode this instance to 64-bit integer."""')
    lines.append("    accumulator = 0")
    lines.append("")

    for layout in layouts:
        field_name = layout.name
        field_def = schema.fields[field_name]

        # Add comment with bit position
        lines.append(f"    # {field_name}: offset={layout.offset}, bits={layout.bits}")

        if layout.nullable:
            # Nullable field: handle None case
            lines.append(f"    if self.{field_name} is not None:")
            lines.append(f"        # Presence bit at offset {layout.offset}")
            lines.append(f"        accumulator |= 1 << {layout.offset}")

            # Generate normalization logic for value
            normalize_expr = _generate_normalize_expression(field_name, field_def)

            # Pack value at offset+1
            value_bits = layout.bits - 1
            if value_bits > 0:
                mask = (1 << value_bits) - 1
                lines.append(f"        # Value bits at offset {layout.offset + 1}")

                if normalize_expr is None:
                    # Complex normalization - handle inline
                    if isinstance(field_def, DateFieldDefinition):
                        _generate_date_encoding_inline(lines, field_name, field_def, "        ")
                        lines.append(f"        accumulator |= (normalized & {mask}) << {layout.offset + 1}")
                    elif isinstance(field_def, BitmaskFieldDefinition):
                        _generate_bitmask_encoding_inline(lines, field_name, field_def, "        ")
                        lines.append(f"        accumulator |= (normalized & {mask}) << {layout.offset + 1}")
                else:
                    lines.append(f"        normalized = {normalize_expr}")
                    lines.append(f"        accumulator |= (normalized & {mask}) << {layout.offset + 1}")
            lines.append("")
        else:
            # Non-nullable field: normalize and pack directly
            normalize_expr = _generate_normalize_expression(field_name, field_def)

            if normalize_expr is None:
                # Complex normalization - handle inline
                if isinstance(field_def, DateFieldDefinition):
                    _generate_date_encoding_inline(lines, field_name, field_def, "    ")
                elif isinstance(field_def, BitmaskFieldDefinition):
                    _generate_bitmask_encoding_inline(lines, field_name, field_def, "    ")
            else:
                lines.append(f"    normalized = {normalize_expr}")

            # Create mask and pack
            if layout.bits > 0:
                mask = (1 << layout.bits) - 1
                lines.append(f"    accumulator |= (normalized & {mask}) << {layout.offset}")
            lines.append("")

    lines.append("    return accumulator")

    return "\n".join(lines)


def _generate_denormalize_statements(
    field_name: str, field_def: FieldDefinition, indent: str = "    "
) -> list[str]:
    """Generate denormalization statements for a field value.

    Args:
        field_name: Name of the field
        field_def: Field definition with type and constraints
        indent: Indentation prefix for generated statements

    Returns:
        List of Python statement strings that denormalize the extracted value

    Note:
        Assumes 'extracted' variable contains the raw bit value.
    """
    if isinstance(field_def, BoolFieldDefinition):
        return [f"{indent}{field_name}_value = bool(extracted)"]
    elif isinstance(field_def, IntFieldDefinition):
        min_value = field_def.min if field_def.min is not None else 0
        if min_value != 0:
            return [f"{indent}{field_name}_value = extracted + {min_value}"]
        else:
            return [f"{indent}{field_name}_value = extracted"]
    elif isinstance(field_def, EnumFieldDefinition):
        values_repr = repr(field_def.values)
        return [f"{indent}{field_name}_value = {values_repr}[extracted]"]
    elif isinstance(field_def, DateFieldDefinition):
        min_date = field_def.min_date
        resolution = field_def.resolution
        statements = [
            f'{indent}min_date = datetime.fromisoformat("{min_date}")',
        ]
        if resolution == "day":
            statements.append(f'{indent}{field_name}_value = (min_date + datetime.timedelta(days=extracted)).date()')
        elif resolution == "hour":
            statements.append(f'{indent}{field_name}_value = min_date + datetime.timedelta(hours=extracted)')
        elif resolution == "minute":
            statements.append(f'{indent}{field_name}_value = min_date + datetime.timedelta(minutes=extracted)')
        elif resolution == "second":
            statements.append(f'{indent}{field_name}_value = min_date + datetime.timedelta(seconds=extracted)')
        return statements
    elif isinstance(field_def, BitmaskFieldDefinition):
        flags_repr = repr(field_def.flags)
        return [
            f'{indent}flags_def = {flags_repr}',
            f'{indent}{field_name}_value = {{}}',
            f'{indent}for flag_name, flag_position in flags_def.items():',
            f'{indent}    {field_name}_value[flag_name] = bool(extracted & (1 << flag_position))',
        ]
    else:
        raise ValueError(f"Unknown field type: {type(field_def)}")


def generate_decode_method(schema: BitSchema, layouts: list[FieldLayout]) -> str:
    """Generate decode() classmethod using bit extraction pattern.

    Args:
        schema: BitSchema with field definitions
        layouts: Field layouts with bit offsets and constraints

    Returns:
        Decode method source code

    Algorithm:
        Mirrors decoder.py logic:
        1. Extract bits at each offset
        2. Denormalize to semantic values
        3. Handle nullable presence bits
        4. Return cls(...) with all fields
    """
    lines = []
    lines.append("@classmethod")
    lines.append("def decode(cls, encoded: int) -> 'ActiveFlag':")
    lines.append('    """Decode 64-bit integer to instance."""')

    field_assignments = []

    for layout in layouts:
        field_name = layout.name
        field_def = schema.fields[field_name]

        lines.append(f"    # {field_name}: offset={layout.offset}, bits={layout.bits}")

        if layout.nullable:
            # Nullable field: check presence bit
            lines.append(f"    presence = (encoded >> {layout.offset}) & 1")
            lines.append(f"    if presence == 0:")
            lines.append(f"        {field_name}_value = None")
            lines.append(f"    else:")

            # Extract value at offset+1
            value_offset = layout.offset + 1
            value_bits = layout.bits - 1
            if value_bits > 0:
                mask = (1 << value_bits) - 1
                lines.append(f"        extracted = (encoded >> {value_offset}) & {mask}")
                # Denormalize
                lines.extend(_generate_denormalize_statements(field_name, field_def, "        "))
            else:
                lines.append(f"        {field_name}_value = True")  # Boolean with 0 value bits

            field_assignments.append(f"{field_name}={field_name}_value")
        else:
            # Non-nullable field: extract directly
            if layout.bits > 0:
                mask = (1 << layout.bits) - 1
                lines.append(f"    extracted = (encoded >> {layout.offset}) & {mask}")
                # Denormalize
                lines.extend(_generate_denormalize_statements(field_name, field_def, "    "))
            else:
                # Zero bits means constant value
                if isinstance(field_def, EnumFieldDefinition):
                    lines.append(f"    {field_name}_value = {repr(field_def.values[0])}")

            field_assignments.append(f"{field_name}={field_name}_value")

        lines.append("")

    # Return statement
    lines.append(f"    return cls({', '.join(field_assignments)})")

    return "\n".join(lines)


def generate_dataclass_code(schema: BitSchema, layouts: list[FieldLayout]) -> str:
    """Generate complete dataclass code from schema and layouts.

    Args:
        schema: BitSchema with field definitions
        layouts: Field layouts with bit offsets

    Returns:
        Complete Python source code for dataclass

    Structure:
        - Module docstring
        - Imports
        - @dataclass decorator
        - Class with fields
        - encode() method
        - decode() classmethod
    """
    # Calculate total bits
    total_bits = sum(layout.bits for layout in layouts)

    # Build field list for docstring
    field_list = []
    for layout in layouts:
        field_def = schema.fields[layout.name]
        type_hint = generate_field_type_hint(layout.name, field_def)
        constraints_str = ""
        if isinstance(field_def, IntFieldDefinition):
            if field_def.min is not None and field_def.max is not None:
                constraints_str = f" ({field_def.min} to {field_def.max})"
        elif isinstance(field_def, EnumFieldDefinition):
            constraints_str = f" (values: {', '.join(field_def.values[:3])}{'...' if len(field_def.values) > 3 else ''})"
        elif isinstance(field_def, DateFieldDefinition):
            constraints_str = f" ({field_def.min_date}..{field_def.max_date}, {field_def.resolution})"
        elif isinstance(field_def, BitmaskFieldDefinition):
            flag_names = ', '.join(list(field_def.flags.keys())[:3])
            if len(field_def.flags) > 3:
                flag_names += '...'
            constraints_str = f" (flags: {flag_names})"
        field_list.append(f"    {layout.name}: {type_hint}{constraints_str}")

    field_list_str = "\n".join(field_list)

    # Module docstring
    module_doc = f'''"""Generated BitSchema dataclass: {schema.name}

Auto-generated from schema. Do not edit manually.

Fields ({total_bits} bits total):
{field_list_str}
"""'''

    # Imports
    imports = "from dataclasses import dataclass"

    # Check if we need datetime imports
    has_date_field = any(isinstance(schema.fields[layout.name], DateFieldDefinition) for layout in layouts)
    if has_date_field:
        imports += "\nimport datetime"

    # Class definition
    class_lines = []
    class_lines.append("@dataclass")
    class_lines.append(f"class {schema.name}:")
    class_lines.append(f'    """BitSchema-encoded dataclass ({total_bits} bits total)."""')
    class_lines.append("")

    # Add fields
    field_defs = generate_field_definitions(schema)
    for line in field_defs.split("\n"):
        class_lines.append(f"    {line}")
    class_lines.append("")

    # Add encode method
    encode_method = generate_encode_method(schema, layouts)
    for line in encode_method.split("\n"):
        class_lines.append(f"    {line}")
    class_lines.append("")

    # Add decode method
    decode_method = generate_decode_method(schema, layouts)
    # Fix the class name in return type hint
    decode_method = decode_method.replace("'ActiveFlag'", f"'{schema.name}'")
    for line in decode_method.split("\n"):
        class_lines.append(f"    {line}")

    # Combine all parts
    code = f"{module_doc}\n\n{imports}\n\n\n" + "\n".join(class_lines) + "\n"

    # Format code
    code = format_generated_code(code)

    # Validate before returning
    validate_generated_code(code)

    return code


def format_generated_code(code: str) -> str:
    """Format generated code using Ruff if available.

    Args:
        code: Python source code to format

    Returns:
        Formatted code if Ruff available, otherwise original code

    Graceful degradation: If Ruff is not installed or fails,
    returns unformatted code rather than raising an error.
    """
    try:
        result = subprocess.run(
            ["ruff", "format", "-"],
            input=code.encode("utf-8"),
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8")
        else:
            # Ruff failed, return original
            return code
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        # Ruff not available or failed, return original
        return code


def validate_generated_code(code: str) -> bool:
    """Validate that generated code is syntactically valid Python.

    Args:
        code: Python source code to validate

    Returns:
        True if valid

    Raises:
        SyntaxError: If code is not valid Python
    """
    ast.parse(code)
    return True
