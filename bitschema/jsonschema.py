"""JSON Schema Draft 2020-12 export for BitSchema schemas.

Generates JSON Schema compliant schemas for interoperability with JSON Schema
tooling, API documentation generators, and validation libraries.
"""

from .models import (
    BitSchema,
    BoolFieldDefinition,
    IntFieldDefinition,
    EnumFieldDefinition,
    FieldDefinition,
)
from .layout import FieldLayout


def generate_json_schema(schema: BitSchema, layouts: list[FieldLayout]) -> dict:
    """Generate JSON Schema Draft 2020-12 compliant dict from BitSchema.

    Args:
        schema: BitSchema definition with field types and constraints
        layouts: Field layouts with bit offsets and metadata

    Returns:
        Dict containing JSON Schema structure compliant with Draft 2020-12

    Example:
        >>> schema = BitSchema(
        ...     version="1",
        ...     name="UserProfile",
        ...     fields={
        ...         "active": BoolFieldDefinition(type="bool", nullable=False),
        ...         "age": IntFieldDefinition(
        ...             type="int", bits=7, signed=False, min=0, max=100
        ...         ),
        ...     },
        ... )
        >>> layouts, total = compute_bit_layout([...])
        >>> json_schema = generate_json_schema(schema, layouts)
        >>> json_schema["$schema"]
        'https://json-schema.org/draft/2020-12/schema'
    """
    # Calculate total bits from layouts
    total_bits = sum(layout.bits for layout in layouts)

    # Base schema structure
    json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://example.com/schemas/{schema.name}.schema.json",
        "type": "object",
        "title": schema.name,
        "description": "BitSchema-generated schema",
        "properties": {},
        "required": [],
        "additionalProperties": False,
        "x-bitschema-version": schema.version,
        "x-bitschema-total-bits": total_bits,
    }

    # Build properties and required array
    for field_name, field_def in schema.fields.items():
        # Map field definition to JSON Schema property
        property_schema = _map_field_to_json_schema(field_def)
        json_schema["properties"][field_name] = property_schema

        # Add to required array if not nullable
        if not field_def.nullable:
            json_schema["required"].append(field_name)

    return json_schema


def _map_field_to_json_schema(field_def: FieldDefinition) -> dict:
    """Map BitSchema field definition to JSON Schema property.

    Args:
        field_def: Field definition (Bool, Int, or Enum)

    Returns:
        Dict containing JSON Schema property definition

    Field type mappings:
        - BoolFieldDefinition → {"type": "boolean"}
        - IntFieldDefinition → {"type": "integer", "minimum": min, "maximum": max}
        - EnumFieldDefinition → {"type": "string", "enum": [values]}
        - Nullable fields → {"type": [base_type, "null"], ...}
    """
    # Boolean field
    if isinstance(field_def, BoolFieldDefinition):
        if field_def.nullable:
            return {"type": ["boolean", "null"]}
        return {"type": "boolean"}

    # Integer field
    elif isinstance(field_def, IntFieldDefinition):
        property_schema = {"type": "integer"}

        # Add constraints if present
        if field_def.min is not None:
            property_schema["minimum"] = field_def.min
        if field_def.max is not None:
            property_schema["maximum"] = field_def.max

        # Handle nullable
        if field_def.nullable:
            property_schema["type"] = ["integer", "null"]

        return property_schema

    # Enum field
    elif isinstance(field_def, EnumFieldDefinition):
        property_schema = {
            "type": "string",
            "enum": field_def.values,
        }

        # Handle nullable
        if field_def.nullable:
            property_schema["type"] = ["string", "null"]

        return property_schema

    # Should never reach here due to type union, but handle gracefully
    else:
        raise ValueError(f"Unknown field type: {type(field_def)}")
