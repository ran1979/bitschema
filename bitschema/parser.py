"""Schema file parser - alias for loader module.

This module provides the parse_schema_file function as specified in the original
design. It's a thin wrapper around the loader module which implements the actual
functionality.

For consistency with existing codebase, use loader.load_schema() directly.
This module exists for backward compatibility and explicit API naming.
"""

from pathlib import Path
from .loader import load_schema as parse_schema_file
from .models import BitSchema

__all__ = ["parse_schema_file"]


# Re-export for direct use
def parse_schema_file(file_path: str | Path) -> BitSchema:
    """Load and validate schema from JSON or YAML file.

    This is an alias for loader.load_schema() with the naming convention
    specified in the original plan.

    Args:
        file_path: Path to schema file (.json or .yaml/.yml)

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If file cannot be read, parsed, or validation fails
        FileNotFoundError: If file does not exist

    Examples:
        >>> from pathlib import Path
        >>> schema = parse_schema_file(Path("schema.json"))
        >>> print(schema.name)
        MySchema

    Security:
        Uses yaml.safe_load() for YAML parsing to prevent code execution attacks.
    """
    from .loader import load_schema
    return load_schema(file_path)
