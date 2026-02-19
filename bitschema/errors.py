"""Custom exception classes for BitSchema validation failures."""


class ValidationError(Exception):
    """Raised when field value validation fails.

    Used for runtime encoding validation where a value violates field constraints
    (e.g., exceeds maximum, out of enum range, wrong type).

    Attributes:
        message: Human-readable error description
        field_name: Name of the field that failed validation (optional)

    Example:
        raise ValidationError("value exceeds maximum", field_name="age")
        # Results in: "Field 'age': value exceeds maximum"
    """

    def __init__(self, message: str, field_name: str | None = None):
        """Initialize validation error with context.

        Args:
            message: Error description
            field_name: Name of field that failed (optional)
        """
        self.message = message
        self.field_name = field_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with field name if provided."""
        if self.field_name:
            return f"Field '{self.field_name}': {self.message}"
        return self.message

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


class EncodingError(Exception):
    """Raised when data encoding validation fails.

    Used for runtime encoding validation where data values violate field constraints
    before encoding (e.g., missing required field, type mismatch, value out of range).

    Attributes:
        message: Human-readable error description
        field_name: Name of the field that failed validation (optional)

    Example:
        raise EncodingError("value 150 exceeds maximum 100", field_name="age")
        # Results in: "Field 'age': value 150 exceeds maximum 100"
    """

    def __init__(self, message: str, field_name: str | None = None):
        """Initialize encoding error with context.

        Args:
            message: Error description
            field_name: Name of field that failed (optional)
        """
        self.message = message
        self.field_name = field_name
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with field name if provided."""
        if self.field_name:
            return f"Field '{self.field_name}': {self.message}"
        return self.message

    def __str__(self) -> str:
        """Return formatted error message."""
        return self._format_message()


class SchemaError(Exception):
    """Raised when schema-level validation fails.

    Used for schema definition errors that prevent bit layout computation
    (e.g., duplicate field names, bit overflow, invalid field types).

    Attributes:
        message: Human-readable error description

    Example:
        raise SchemaError("Schema exceeds 64-bit limit: 72 bits total")
    """

    def __init__(self, message: str):
        """Initialize schema error.

        Args:
            message: Error description
        """
        self.message = message
        super().__init__(message)
