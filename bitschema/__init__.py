"""BitSchema: Bit-level data packing with mathematical correctness."""

__version__ = "0.1.0"

# Core models
from .models import (
    BitSchema,
    IntFieldDefinition,
    BoolFieldDefinition,
    EnumFieldDefinition,
    FieldDefinition,
)

# Schema loading
from .loader import (
    load_schema,
    load_from_json,
    load_from_yaml,
    schema_from_dict,
    schema_to_json,
    schema_to_dict,
)

# File parsing
from .parser import parse_schema_file

# Bit layout computation
from .layout import compute_bit_layout, FieldLayout

# Output generation
from .output import generate_output_schema

# Runtime validation
from .validator import validate_data, validate_field_value

# Encoding
from .encoder import encode, normalize_value

# Decoding
from .decoder import decode, denormalize_value

# Code generation
from .codegen import generate_dataclass_code

# JSON Schema export
from .jsonschema import generate_json_schema

# Visualization
from .visualization import (
    visualize_bit_layout,
    visualize_bit_layout_ascii,
    visualize_bit_layout_markdown,
    format_bit_range,
    format_constraints,
)

# Exceptions
from .errors import ValidationError, SchemaError, EncodingError

__all__ = [
    # Version
    "__version__",
    # Models
    "BitSchema",
    "IntFieldDefinition",
    "BoolFieldDefinition",
    "EnumFieldDefinition",
    "FieldDefinition",
    # Loading
    "load_schema",
    "load_from_json",
    "load_from_yaml",
    "schema_from_dict",
    "schema_to_json",
    "schema_to_dict",
    # File parsing
    "parse_schema_file",
    # Layout computation
    "compute_bit_layout",
    "FieldLayout",
    # Output generation
    "generate_output_schema",
    # Runtime validation
    "validate_data",
    "validate_field_value",
    # Encoding
    "encode",
    "normalize_value",
    # Decoding
    "decode",
    "denormalize_value",
    # Code generation
    "generate_dataclass_code",
    # JSON Schema export
    "generate_json_schema",
    # Visualization
    "visualize_bit_layout",
    "visualize_bit_layout_ascii",
    "visualize_bit_layout_markdown",
    "format_bit_range",
    "format_constraints",
    # Exceptions
    "ValidationError",
    "SchemaError",
    "EncodingError",
]
