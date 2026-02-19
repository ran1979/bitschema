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
    # Exceptions
    "ValidationError",
    "SchemaError",
    "EncodingError",
]
