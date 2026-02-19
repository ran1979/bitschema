"""Runtime data validation for encoding preparation.

Validates data dict values against FieldLayout constraints before encoding,
implementing fail-fast validation to prevent silent corruption.
"""

from typing import Any

from .layout import FieldLayout
from .errors import EncodingError


def validate_field_value(value: Any, layout: FieldLayout) -> None:
    """Validate a single field value against its layout constraints.

    Checks type correctness and constraint satisfaction before encoding.
    Fails fast with clear error messages including field name and violated constraint.

    Args:
        value: The value to validate
        layout: Field layout with type and constraints

    Raises:
        EncodingError: If value violates type or constraint requirements

    Validation rules:
        - None allowed only for nullable fields
        - Boolean: must be bool type
        - Integer: must be int type and within min/max range
        - Enum: must be in allowed values list

    Examples:
        >>> layout = FieldLayout(name="age", type="integer", offset=0, bits=7,
        ...                      constraints={"min": 0, "max": 100})
        >>> validate_field_value(50, layout)  # OK
        >>> validate_field_value(150, layout)  # Raises EncodingError
    """
    # Handle None values
    if value is None:
        if not layout.nullable:
            raise EncodingError(
                "cannot be None (field is not nullable)", field_name=layout.name
            )
        return  # None is valid for nullable fields

    # Type-specific validation
    if layout.type == "boolean":
        if not isinstance(value, bool):
            raise EncodingError(
                f"expected boolean, got {type(value).__name__}",
                field_name=layout.name,
            )

    elif layout.type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            # Note: isinstance(True, int) is True in Python, so exclude bool explicitly
            raise EncodingError(
                f"expected integer, got {type(value).__name__}",
                field_name=layout.name,
            )

        # Check min/max constraints
        min_value = layout.constraints.get("min")
        max_value = layout.constraints.get("max")

        if min_value is not None and value < min_value:
            raise EncodingError(
                f"value {value} is below minimum {min_value}",
                field_name=layout.name,
            )

        if max_value is not None and value > max_value:
            raise EncodingError(
                f"value {value} exceeds maximum {max_value}",
                field_name=layout.name,
            )

    elif layout.type == "enum":
        allowed_values = layout.constraints.get("values", [])
        if value not in allowed_values:
            raise EncodingError(
                f"value '{value}' not in allowed values {allowed_values}",
                field_name=layout.name,
            )


def validate_data(data: dict, layouts: list[FieldLayout]) -> None:
    """Validate complete data dict against field layouts.

    Checks that all required fields are present and all field values
    satisfy their constraints. Fails fast on first error.

    Args:
        data: Dictionary mapping field names to values
        layouts: List of field layouts with constraints

    Raises:
        EncodingError: If required field missing or value validation fails

    Validation rules:
        - All non-nullable fields must be present in data dict
        - Nullable fields can be omitted (treated as None)
        - Each present field value must pass validate_field_value
        - Extra fields in data dict are allowed (ignored)

    Examples:
        >>> layouts = [
        ...     FieldLayout(name="active", type="boolean", offset=0, bits=1,
        ...                 constraints={}, nullable=False),
        ...     FieldLayout(name="age", type="integer", offset=1, bits=7,
        ...                 constraints={"min": 0, "max": 100}, nullable=False),
        ... ]
        >>> validate_data({"active": True, "age": 25}, layouts)  # OK
        >>> validate_data({"active": True}, layouts)  # Raises EncodingError (missing age)
    """
    # Build set of required field names (non-nullable fields)
    required_fields = {layout.name for layout in layouts if not layout.nullable}

    # Check for missing required fields
    provided_fields = set(data.keys())
    missing_fields = required_fields - provided_fields

    if missing_fields:
        missing_list = sorted(missing_fields)
        if len(missing_list) == 1:
            raise EncodingError(f"required field '{missing_list[0]}' is missing")
        else:
            raise EncodingError(
                f"required fields missing: {', '.join(repr(f) for f in missing_list)}"
            )

    # Validate each field value
    for layout in layouts:
        # Get value from data dict (None if not present)
        value = data.get(layout.name)

        # Validate the value
        validate_field_value(value, layout)
