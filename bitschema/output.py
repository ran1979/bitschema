"""Output schema generation for BitSchema.

Generates JSON-serializable schema output with complete bit layout metadata.
Implements OUTPUT-01, OUTPUT-02, OUTPUT-03 requirements.
"""

from .models import BitSchema
from .layout import FieldLayout


def generate_output_schema(
    schema: BitSchema,
    layouts: list[FieldLayout],
    total_bits: int
) -> dict:
    """Generate JSON schema output with bit layout metadata.

    Creates a complete output schema in JSON-serializable format containing:
    - Schema version
    - Total bit count
    - Per-field metadata: name, type, offset, bits, constraints

    Args:
        schema: Validated BitSchema model
        layouts: Computed field layouts with bit offsets
        total_bits: Total bits required for schema

    Returns:
        Dictionary with keys:
            - version: Schema version (matches input schema)
            - total_bits: Total bits for all fields
            - fields: List of field metadata dicts

    Each field dict contains:
        - name: Field name
        - type: Field type (boolean, integer, enum)
        - offset: Starting bit position (0-indexed from LSB)
        - bits: Number of bits allocated
        - constraints: Type-specific constraints dict
            - Boolean: {} (empty)
            - Integer: {"min": <min>, "max": <max>}
            - Enum: {"values": [<values>]}

    Example:
        >>> schema = BitSchema(version="1", name="Test", fields={...})
        >>> layouts, total = compute_bit_layout(schema.fields)
        >>> output = generate_output_schema(schema, layouts, total)
        >>> output["total_bits"]
        10
        >>> output["fields"][0]
        {"name": "active", "type": "boolean", "offset": 0, "bits": 1, "constraints": {}}

    Requirements:
        - OUTPUT-01: JSON schema with version and total_bits
        - OUTPUT-02: Per-field metadata (name, type, offset, bits, constraints)
        - OUTPUT-03: Output is JSON-serializable (no custom types)
    """
    # Build output structure
    output = {
        "version": schema.version,
        "total_bits": total_bits,
        "fields": []
    }

    # Add each field with complete metadata
    for layout in layouts:
        field_dict = {
            "name": layout.name,
            "type": layout.type,
            "offset": layout.offset,
            "bits": layout.bits,
            "constraints": layout.constraints
        }
        output["fields"].append(field_dict)

    return output
