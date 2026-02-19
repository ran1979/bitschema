"""Schema loader for JSON and YAML formats with validation.

Provides functions to load and validate BitSchema definitions from
JSON or YAML files, returning validated Pydantic models.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from .models import BitSchema
from .errors import SchemaError


def load_schema(file_path: str | Path) -> BitSchema:
    """Load and validate schema from JSON or YAML file.

    Args:
        file_path: Path to schema file (.json or .yaml/.yml)

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If file cannot be read, parsed, or validation fails
        FileNotFoundError: If file does not exist
    """
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")

    # Read file content
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise SchemaError(f"Failed to read schema file '{path}': {e}")

    # Determine format and parse
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_from_json(content, str(path))
    elif suffix in (".yaml", ".yml"):
        return load_from_yaml(content, str(path))
    else:
        raise SchemaError(
            f"Unsupported file format '{suffix}'. Use .json, .yaml, or .yml"
        )


def load_from_json(json_content: str, source_name: str = "<json>") -> BitSchema:
    """Parse and validate schema from JSON string.

    Args:
        json_content: JSON string containing schema definition
        source_name: Name to use in error messages (default: "<json>")

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If JSON is invalid or validation fails
    """
    # Parse JSON
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise SchemaError(f"Invalid JSON in '{source_name}': {e}")

    # Validate with Pydantic
    return _validate_schema_data(data, source_name)


def load_from_yaml(yaml_content: str, source_name: str = "<yaml>") -> BitSchema:
    """Parse and validate schema from YAML string.

    Args:
        yaml_content: YAML string containing schema definition
        source_name: Name to use in error messages (default: "<yaml>")

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If YAML is invalid or validation fails
    """
    # Import yaml lazily (optional dependency)
    try:
        import yaml
    except ImportError:
        raise SchemaError(
            "PyYAML is required for YAML support. Install with: pip install pyyaml"
        )

    # Parse YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise SchemaError(f"Invalid YAML in '{source_name}': {e}")

    # Validate with Pydantic
    return _validate_schema_data(data, source_name)


def _validate_schema_data(data: Any, source_name: str) -> BitSchema:
    """Validate parsed schema data with Pydantic.

    Args:
        data: Parsed schema dictionary
        source_name: Name to use in error messages

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If validation fails
    """
    try:
        return BitSchema.model_validate(data)
    except PydanticValidationError as e:
        # Convert Pydantic validation errors to SchemaError with friendly message
        errors = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            errors.append(f"  {loc}: {msg}")

        error_list = "\n".join(errors)
        raise SchemaError(
            f"Schema validation failed in '{source_name}':\n{error_list}"
        )


def schema_from_dict(data: dict[str, Any]) -> BitSchema:
    """Create validated schema from dictionary (programmatic API).

    Args:
        data: Schema definition as dictionary

    Returns:
        Validated BitSchema model

    Raises:
        SchemaError: If validation fails
    """
    return _validate_schema_data(data, "<dict>")


def schema_to_json(schema: BitSchema, indent: int = 2) -> str:
    """Serialize schema to JSON string.

    Args:
        schema: Validated BitSchema model
        indent: JSON indentation level (default: 2)

    Returns:
        JSON string representation
    """
    return schema.model_dump_json(indent=indent, exclude_none=True)


def schema_to_dict(schema: BitSchema) -> dict[str, Any]:
    """Convert schema to dictionary.

    Args:
        schema: Validated BitSchema model

    Returns:
        Dictionary representation (JSON-serializable)
    """
    return schema.model_dump(exclude_none=True)
