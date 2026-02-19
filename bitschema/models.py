"""Pydantic models for BitSchema schema definition with Zod integration.

This module defines the validated models for schema and field definitions.
Uses Pydantic v2 for runtime validation with Zod-like schema generation.
"""

from typing import Literal, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class IntFieldDefinition(BaseModel):
    """Integer field definition with bit-level constraints.

    Attributes:
        type: Must be "int"
        bits: Number of bits to allocate (1-64)
        signed: Whether to support negative values
        nullable: Whether field can be null (adds presence bit)
        min: Minimum allowed value (optional constraint)
        max: Maximum allowed value (optional constraint)
    """

    type: Literal["int"] = "int"
    bits: Annotated[int, Field(ge=1, le=64, description="Number of bits (1-64)")]
    signed: bool = Field(default=False, description="Support negative values")
    nullable: bool = Field(default=False, description="Allow null values")
    min: int | None = Field(default=None, description="Minimum value constraint")
    max: int | None = Field(default=None, description="Maximum value constraint")

    @field_validator("bits")
    @classmethod
    def validate_bits(cls, v: int) -> int:
        """Ensure bits is in valid range."""
        if not 1 <= v <= 64:
            raise ValueError(f"bits must be between 1 and 64, got {v}")
        return v

    @model_validator(mode="after")
    def validate_constraints(self) -> "IntFieldDefinition":
        """Validate min/max constraints are within bit range."""
        # Calculate theoretical range for this bit configuration
        if self.signed:
            theoretical_min = -(2 ** (self.bits - 1))
            theoretical_max = 2 ** (self.bits - 1) - 1
        else:
            theoretical_min = 0
            theoretical_max = 2 ** self.bits - 1

        # Validate min constraint
        if self.min is not None:
            if self.min < theoretical_min:
                raise ValueError(
                    f"min={self.min} cannot be represented in {self.bits} "
                    f"{'signed' if self.signed else 'unsigned'} bits "
                    f"(range: {theoretical_min} to {theoretical_max})"
                )
            if self.min > theoretical_max:
                raise ValueError(
                    f"min={self.min} exceeds maximum representable value {theoretical_max}"
                )

        # Validate max constraint
        if self.max is not None:
            if self.max > theoretical_max:
                raise ValueError(
                    f"max={self.max} cannot be represented in {self.bits} "
                    f"{'signed' if self.signed else 'unsigned'} bits "
                    f"(range: {theoretical_min} to {theoretical_max})"
                )
            if self.max < theoretical_min:
                raise ValueError(
                    f"max={self.max} is below minimum representable value {theoretical_min}"
                )

        # Validate min <= max
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError(f"min={self.min} cannot be greater than max={self.max}")

        return self


class BoolFieldDefinition(BaseModel):
    """Boolean field definition.

    Attributes:
        type: Must be "bool"
        nullable: Whether field can be null (adds presence bit)
    """

    type: Literal["bool"] = "bool"
    nullable: bool = Field(default=False, description="Allow null values")


class EnumFieldDefinition(BaseModel):
    """Enumeration field definition.

    Attributes:
        type: Must be "enum"
        values: List of allowed string values (1-255 variants)
        nullable: Whether field can be null (adds presence bit)
    """

    type: Literal["enum"] = "enum"
    values: Annotated[
        list[str],
        Field(min_length=1, max_length=255, description="Allowed values (1-255)")
    ]
    nullable: bool = Field(default=False, description="Allow null values")

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: list[str]) -> list[str]:
        """Ensure values are unique and non-empty."""
        if not v:
            raise ValueError("enum must have at least one value")
        if len(v) > 255:
            raise ValueError(f"enum can have at most 255 values, got {len(v)}")

        # Check for duplicates
        if len(v) != len(set(v)):
            duplicates = [val for val in v if v.count(val) > 1]
            raise ValueError(f"enum values must be unique, found duplicates: {set(duplicates)}")

        # Check for empty strings
        if "" in v:
            raise ValueError("enum values cannot be empty strings")

        return v

    @property
    def bits_required(self) -> int:
        """Calculate bits needed to represent all enum values."""
        return (len(self.values) - 1).bit_length()


class DateFieldDefinition(BaseModel):
    """Date/datetime field definition with configurable resolution.

    Attributes:
        type: Must be "date"
        resolution: Time resolution (day, hour, minute, second)
        min_date: Minimum date in ISO 8601 format
        max_date: Maximum date in ISO 8601 format
        nullable: Whether field can be null (adds presence bit)
        description: Optional field description
    """

    type: Literal["date"] = "date"
    resolution: Literal["day", "hour", "minute", "second"]
    min_date: str = Field(description="Minimum date (ISO 8601)")
    max_date: str = Field(description="Maximum date (ISO 8601)")
    nullable: bool = Field(default=False, description="Allow null values")
    description: str | None = Field(default=None, description="Field description")

    @field_validator("min_date", "max_date")
    @classmethod
    def validate_iso_date(cls, v: str) -> str:
        """Validate ISO 8601 date format."""
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 date: {v}") from e

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateFieldDefinition":
        """Validate min_date is before max_date."""
        min_dt = datetime.fromisoformat(self.min_date)
        max_dt = datetime.fromisoformat(self.max_date)
        if min_dt >= max_dt:
            raise ValueError("min_date must be before max_date")
        return self


class BitmaskFieldDefinition(BaseModel):
    """Bitmask field definition for storing multiple boolean flags.

    Attributes:
        type: Must be "bitmask"
        flags: Dictionary mapping flag names to bit positions (0-63)
        nullable: Whether field can be null (adds presence bit)
        description: Optional field description
    """

    type: Literal["bitmask"] = "bitmask"
    flags: dict[str, int] = Field(description="Flag names to bit positions (0-63)")
    nullable: bool = Field(default=False, description="Allow null values")
    description: str | None = Field(default=None, description="Field description")

    @field_validator("flags")
    @classmethod
    def validate_flags(cls, v: dict[str, int]) -> dict[str, int]:
        """Validate flag definitions."""
        if not v:
            raise ValueError("bitmask must have at least one flag")

        # Check unique positions
        positions = list(v.values())
        if len(set(positions)) != len(positions):
            raise ValueError("flag positions must be unique")

        # Check 0-63 range
        if any(pos < 0 or pos > 63 for pos in positions):
            raise ValueError("flag positions must be 0-63 for 64-bit limit")

        # Check valid Python identifiers
        for name in v.keys():
            if not name.isidentifier():
                raise ValueError(f"flag name '{name}' must be valid Python identifier")

        return v


# Union type for all field definitions
FieldDefinition = IntFieldDefinition | BoolFieldDefinition | EnumFieldDefinition | DateFieldDefinition | BitmaskFieldDefinition


class BitSchema(BaseModel):
    """Complete schema definition with validation.

    Attributes:
        version: Schema format version (currently only "1")
        name: Schema name for generated code
        fields: Dictionary of field_name -> field_definition
    """

    version: Literal["1"] = "1"
    name: Annotated[str, Field(min_length=1, pattern=r'^[A-Za-z_][A-Za-z0-9_]*$')]
    fields: dict[str, IntFieldDefinition | BoolFieldDefinition | EnumFieldDefinition | DateFieldDefinition | BitmaskFieldDefinition]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is valid Python identifier."""
        if not v:
            raise ValueError("name cannot be empty")
        if not v.isidentifier():
            raise ValueError(
                f"name must be valid Python identifier (alphanumeric + underscore, "
                f"cannot start with digit), got '{v}'"
            )
        return v

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: dict) -> dict:
        """Ensure at least one field is defined."""
        if not v:
            raise ValueError("schema must have at least one field")
        return v

    @model_validator(mode="after")
    def validate_total_bits(self) -> "BitSchema":
        """Ensure total schema fits in 64 bits."""
        total_bits = 0

        for field_name, field_def in self.fields.items():
            if isinstance(field_def, IntFieldDefinition):
                total_bits += field_def.bits
            elif isinstance(field_def, BoolFieldDefinition):
                total_bits += 1
            elif isinstance(field_def, EnumFieldDefinition):
                total_bits += field_def.bits_required
            elif isinstance(field_def, DateFieldDefinition):
                # Calculate date field bits based on resolution
                min_dt = datetime.fromisoformat(field_def.min_date)
                max_dt = datetime.fromisoformat(field_def.max_date)
                if field_def.resolution == "day":
                    total_units = (max_dt - min_dt).days
                elif field_def.resolution == "hour":
                    total_units = int((max_dt - min_dt).total_seconds() / 3600)
                elif field_def.resolution == "minute":
                    total_units = int((max_dt - min_dt).total_seconds() / 60)
                elif field_def.resolution == "second":
                    total_units = int((max_dt - min_dt).total_seconds())
                total_bits += (total_units - 1).bit_length() if total_units > 0 else 0
            elif isinstance(field_def, BitmaskFieldDefinition):
                # Bitmask bits = max(flag_positions) + 1
                max_position = max(field_def.flags.values())
                total_bits += max_position + 1

            # Add presence bit if nullable
            if field_def.nullable:
                total_bits += 1

        if total_bits > 64:
            raise ValueError(
                f"Schema exceeds 64-bit limit: {total_bits} bits total. "
                f"Reduce field sizes or number of fields."
            )

        return self

    def calculate_total_bits(self) -> int:
        """Calculate total bits required for this schema."""
        total = 0
        for field_def in self.fields.values():
            if isinstance(field_def, IntFieldDefinition):
                total += field_def.bits
            elif isinstance(field_def, BoolFieldDefinition):
                total += 1
            elif isinstance(field_def, EnumFieldDefinition):
                total += field_def.bits_required
            elif isinstance(field_def, DateFieldDefinition):
                # Calculate date field bits based on resolution
                min_dt = datetime.fromisoformat(field_def.min_date)
                max_dt = datetime.fromisoformat(field_def.max_date)
                if field_def.resolution == "day":
                    total_units = (max_dt - min_dt).days
                elif field_def.resolution == "hour":
                    total_units = int((max_dt - min_dt).total_seconds() / 3600)
                elif field_def.resolution == "minute":
                    total_units = int((max_dt - min_dt).total_seconds() / 60)
                elif field_def.resolution == "second":
                    total_units = int((max_dt - min_dt).total_seconds())
                total += (total_units - 1).bit_length() if total_units > 0 else 0
            elif isinstance(field_def, BitmaskFieldDefinition):
                # Bitmask bits = max(flag_positions) + 1
                max_position = max(field_def.flags.values())
                total += max_position + 1

            if field_def.nullable:
                total += 1

        return total
