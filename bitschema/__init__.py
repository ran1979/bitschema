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

# Exceptions
from .errors import ValidationError, SchemaError

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
    # Exceptions
    "ValidationError",
    "SchemaError",
]
