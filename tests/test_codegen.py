"""Tests for dataclass code generation from BitSchema schemas.

Tests the generation of type-safe dataclass code with encode/decode methods
that match runtime encoder/decoder behavior exactly.
"""

import ast
import pytest

from bitschema import (
    BitSchema,
    IntFieldDefinition,
    BoolFieldDefinition,
    EnumFieldDefinition,
    compute_bit_layout,
    encode,
    decode,
)
from bitschema.codegen import (
    generate_field_type_hint,
    generate_field_definitions,
    generate_encode_method,
    generate_decode_method,
    generate_dataclass_code,
    format_generated_code,
    validate_generated_code,
)


class TestFieldTypeHints:
    """Test type hint generation for different field types."""

    def test_generate_boolean_field_type_hint(self):
        """Boolean field should generate 'bool' type hint."""
        field_def = BoolFieldDefinition(type="bool")
        result = generate_field_type_hint("active", field_def)
        assert result == "bool"

    def test_generate_integer_field_type_hint(self):
        """Integer field should generate 'int' type hint."""
        field_def = IntFieldDefinition(type="int", bits=8, min=0, max=255)
        result = generate_field_type_hint("age", field_def)
        assert result == "int"

    def test_generate_enum_field_type_hint(self):
        """Enum field should generate 'str' type hint."""
        field_def = EnumFieldDefinition(type="enum", values=["idle", "active", "done"])
        result = generate_field_type_hint("status", field_def)
        assert result == "str"

    def test_generate_nullable_boolean_type_hint(self):
        """Nullable boolean should generate 'bool | None' type hint."""
        field_def = BoolFieldDefinition(type="bool", nullable=True)
        result = generate_field_type_hint("active", field_def)
        assert result == "bool | None"

    def test_generate_nullable_integer_type_hint(self):
        """Nullable integer should generate 'int | None' type hint."""
        field_def = IntFieldDefinition(type="int", bits=8, min=0, max=255, nullable=True)
        result = generate_field_type_hint("age", field_def)
        assert result == "int | None"

    def test_generate_nullable_enum_type_hint(self):
        """Nullable enum should generate 'str | None' type hint."""
        field_def = EnumFieldDefinition(
            type="enum", values=["idle", "active", "done"], nullable=True
        )
        result = generate_field_type_hint("status", field_def)
        assert result == "str | None"


class TestFieldDefinitions:
    """Test field definition generation for dataclass."""

    def test_generate_single_boolean_field(self):
        """Single boolean field should generate correct definition."""
        schema = BitSchema(
            version="1",
            name="ActiveFlag",
            fields={"active": BoolFieldDefinition(type="bool")},
        )
        result = generate_field_definitions(schema)
        assert "active: bool" in result

    def test_generate_single_integer_field(self):
        """Single integer field should generate correct definition."""
        schema = BitSchema(
            version="1",
            name="Age",
            fields={"age": IntFieldDefinition(type="int", bits=8, min=0, max=127)},
        )
        result = generate_field_definitions(schema)
        assert "age: int" in result

    def test_generate_nullable_field_with_default(self):
        """Nullable field should generate definition with default None."""
        schema = BitSchema(
            version="1",
            name="OptionalAge",
            fields={
                "age": IntFieldDefinition(
                    type="int", bits=8, min=0, max=127, nullable=True
                )
            },
        )
        result = generate_field_definitions(schema)
        assert "age: int | None = None" in result

    def test_generate_multi_field_definitions(self):
        """Multiple fields should be generated in order."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
                "status": EnumFieldDefinition(
                    type="enum", values=["idle", "active", "done"]
                ),
            },
        )
        result = generate_field_definitions(schema)
        assert "active: bool" in result
        assert "age: int" in result
        assert "status: str" in result


class TestEncodeMethodGeneration:
    """Test encode() method code generation."""

    def test_generate_encode_for_single_boolean(self):
        """Encode method for boolean should use LSB-first accumulator pattern."""
        schema = BitSchema(
            version="1",
            name="ActiveFlag",
            fields={"active": BoolFieldDefinition(type="bool")},
        )
        layouts, _ = compute_bit_layout(
            [{"name": "active", "type": "boolean"}]
        )
        result = generate_encode_method(schema, layouts)

        # Should contain method signature
        assert "def encode(self) -> int:" in result
        # Should contain accumulator initialization
        assert "accumulator = 0" in result
        # Should contain field encoding logic
        assert "active" in result

    def test_generate_encode_for_integer_with_min(self):
        """Encode method for integer should normalize by subtracting min."""
        schema = BitSchema(
            version="1",
            name="Temperature",
            fields={
                "temp": IntFieldDefinition(type="int", bits=8, signed=True, min=-50, max=50)
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "temp", "type": "integer", "min": -50, "max": 50}]
        )
        result = generate_encode_method(schema, layouts)

        # Should contain normalization logic
        assert "temp" in result
        assert "-50" in result or "min" in result

    def test_generate_encode_for_enum(self):
        """Encode method for enum should use index lookup."""
        schema = BitSchema(
            version="1",
            name="Status",
            fields={
                "status": EnumFieldDefinition(
                    type="enum", values=["idle", "active", "done"]
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "status", "type": "enum", "values": ["idle", "active", "done"]}]
        )
        result = generate_encode_method(schema, layouts)

        # Should contain enum values and index lookup
        assert "status" in result
        assert "index" in result or "idle" in result

    def test_generate_encode_for_nullable_field(self):
        """Encode method for nullable should handle presence bit."""
        schema = BitSchema(
            version="1",
            name="OptionalAge",
            fields={
                "age": IntFieldDefinition(
                    type="int", bits=8, min=0, max=127, nullable=True
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "age", "type": "integer", "min": 0, "max": 127, "nullable": True}]
        )
        result = generate_encode_method(schema, layouts)

        # Should handle None case
        assert "None" in result or "is None" in result


class TestDecodeMethodGeneration:
    """Test decode() classmethod code generation."""

    def test_generate_decode_for_single_boolean(self):
        """Decode method should extract bits and denormalize."""
        schema = BitSchema(
            version="1",
            name="ActiveFlag",
            fields={"active": BoolFieldDefinition(type="bool")},
        )
        layouts, _ = compute_bit_layout(
            [{"name": "active", "type": "boolean"}]
        )
        result = generate_decode_method(schema, layouts)

        # Should contain classmethod signature
        assert "@classmethod" in result or "classmethod" in result
        assert "def decode(cls, encoded: int)" in result
        # Should contain bit extraction pattern
        assert ">>" in result and "&" in result
        # Should return instance
        assert "cls(" in result or "return" in result

    def test_generate_decode_for_integer_with_min(self):
        """Decode method should denormalize by adding min."""
        schema = BitSchema(
            version="1",
            name="Temperature",
            fields={
                "temp": IntFieldDefinition(type="int", bits=8, signed=True, min=-50, max=50)
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "temp", "type": "integer", "min": -50, "max": 50}]
        )
        result = generate_decode_method(schema, layouts)

        # Should contain denormalization (add min)
        assert "temp" in result
        assert "-50" in result or "min" in result or "+" in result

    def test_generate_decode_for_enum(self):
        """Decode method should map index to enum value."""
        schema = BitSchema(
            version="1",
            name="Status",
            fields={
                "status": EnumFieldDefinition(
                    type="enum", values=["idle", "active", "done"]
                )
            },
        )
        layouts, _ = compute_bit_layout(
            [{"name": "status", "type": "enum", "values": ["idle", "active", "done"]}]
        )
        result = generate_decode_method(schema, layouts)

        # Should contain enum values list
        assert "idle" in result or "status" in result


class TestDataclassGeneration:
    """Test complete dataclass code generation."""

    def test_generate_single_field_dataclass(self):
        """Should generate complete dataclass with single field."""
        schema = BitSchema(
            version="1",
            name="ActiveFlag",
            fields={"active": BoolFieldDefinition(type="bool")},
        )
        layouts, total_bits = compute_bit_layout(
            [{"name": "active", "type": "boolean"}]
        )
        result = generate_dataclass_code(schema, layouts)

        # Should have dataclass decorator
        assert "@dataclass" in result
        # Should have class definition
        assert "class ActiveFlag:" in result
        # Should have field
        assert "active: bool" in result
        # Should have encode method
        assert "def encode(self)" in result
        # Should have decode method
        assert "def decode(cls" in result

    def test_generate_multi_field_dataclass(self):
        """Should generate dataclass with multiple fields."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
                "status": EnumFieldDefinition(
                    type="enum", values=["idle", "active", "done"]
                ),
            },
        )
        layouts, total_bits = compute_bit_layout([
            {"name": "active", "type": "boolean"},
            {"name": "age", "type": "integer", "min": 0, "max": 127},
            {"name": "status", "type": "enum", "values": ["idle", "active", "done"]},
        ])
        result = generate_dataclass_code(schema, layouts)

        assert "class Person:" in result
        assert "active: bool" in result
        assert "age: int" in result
        assert "status: str" in result

    def test_generated_code_is_valid_python(self):
        """Generated code should be syntactically valid Python."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
            },
        )
        layouts, _ = compute_bit_layout([
            {"name": "active", "type": "boolean"},
            {"name": "age", "type": "integer", "min": 0, "max": 127},
        ])
        code = generate_dataclass_code(schema, layouts)

        # Should validate without raising SyntaxError
        assert validate_generated_code(code) is True

        # Should parse with ast
        ast.parse(code)  # Raises SyntaxError if invalid

    def test_generated_code_includes_docstring(self):
        """Generated code should include helpful docstrings."""
        schema = BitSchema(
            version="1",
            name="ActiveFlag",
            fields={"active": BoolFieldDefinition(type="bool")},
        )
        layouts, total_bits = compute_bit_layout(
            [{"name": "active", "type": "boolean"}]
        )
        result = generate_dataclass_code(schema, layouts)

        # Should contain docstring with field information
        assert '"""' in result
        # Should mention bit count
        assert "bit" in result.lower() or str(total_bits) in result


class TestRoundTripCorrectness:
    """Test that generated code produces same results as runtime encoder/decoder."""

    def test_generated_encode_matches_runtime(self):
        """Generated encode() should produce same output as runtime encoder."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
            },
        )
        layouts, _ = compute_bit_layout([
            {"name": "active", "type": "boolean"},
            {"name": "age", "type": "integer", "min": 0, "max": 127},
        ])

        # Generate code
        code = generate_dataclass_code(schema, layouts)

        # Execute generated code to get class
        namespace = {}
        exec(code, namespace)
        PersonClass = namespace["Person"]

        # Test data
        data = {"active": True, "age": 42}

        # Runtime encoding
        runtime_encoded = encode(data, layouts)

        # Generated encoding
        instance = PersonClass(active=True, age=42)
        generated_encoded = instance.encode()

        # Should match
        assert generated_encoded == runtime_encoded

    def test_generated_decode_matches_runtime(self):
        """Generated decode() should produce same output as runtime decoder."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
            },
        )
        layouts, _ = compute_bit_layout([
            {"name": "active", "type": "boolean"},
            {"name": "age", "type": "integer", "min": 0, "max": 127},
        ])

        # Generate code
        code = generate_dataclass_code(schema, layouts)

        # Execute generated code to get class
        namespace = {}
        exec(code, namespace)
        PersonClass = namespace["Person"]

        # Test encoded value
        encoded = 85  # active=True (bit 0), age=42 (bits 1-7)

        # Runtime decoding
        runtime_decoded = decode(encoded, layouts)

        # Generated decoding
        generated_instance = PersonClass.decode(encoded)
        generated_decoded = {
            "active": generated_instance.active,
            "age": generated_instance.age,
        }

        # Should match
        assert generated_decoded == runtime_decoded

    def test_round_trip_with_generated_code(self):
        """Generated encode → decode should return original values."""
        schema = BitSchema(
            version="1",
            name="Person",
            fields={
                "active": BoolFieldDefinition(type="bool"),
                "age": IntFieldDefinition(type="int", bits=7, min=0, max=127),
                "status": EnumFieldDefinition(
                    type="enum", values=["idle", "active", "done"]
                ),
            },
        )
        layouts, _ = compute_bit_layout([
            {"name": "active", "type": "boolean"},
            {"name": "age", "type": "integer", "min": 0, "max": 127},
            {"name": "status", "type": "enum", "values": ["idle", "active", "done"]},
        ])

        # Generate code
        code = generate_dataclass_code(schema, layouts)

        # Execute generated code to get class
        namespace = {}
        exec(code, namespace)
        PersonClass = namespace["Person"]

        # Original data
        original = PersonClass(active=True, age=42, status="active")

        # Round trip: encode → decode
        encoded = original.encode()
        decoded = PersonClass.decode(encoded)

        # Should match original
        assert decoded.active == original.active
        assert decoded.age == original.age
        assert decoded.status == original.status

    def test_round_trip_with_nullable_fields(self):
        """Generated code should handle nullable fields correctly."""
        schema = BitSchema(
            version="1",
            name="OptionalPerson",
            fields={
                "age": IntFieldDefinition(
                    type="int", bits=8, min=0, max=127, nullable=True
                ),
            },
        )
        layouts, _ = compute_bit_layout([
            {"name": "age", "type": "integer", "min": 0, "max": 127, "nullable": True},
        ])

        # Generate code
        code = generate_dataclass_code(schema, layouts)

        # Execute generated code to get class
        namespace = {}
        exec(code, namespace)
        OptionalPersonClass = namespace["OptionalPerson"]

        # Test with None
        none_instance = OptionalPersonClass(age=None)
        none_encoded = none_instance.encode()
        none_decoded = OptionalPersonClass.decode(none_encoded)
        assert none_decoded.age is None

        # Test with value
        value_instance = OptionalPersonClass(age=42)
        value_encoded = value_instance.encode()
        value_decoded = OptionalPersonClass.decode(value_encoded)
        assert value_decoded.age == 42


class TestCodeFormatting:
    """Test code formatting functionality."""

    def test_format_generated_code_returns_string(self):
        """format_generated_code should always return a string."""
        code = "class Test:\n    pass"
        result = format_generated_code(code)
        assert isinstance(result, str)
        # Should return either formatted or original code
        assert len(result) > 0

    def test_validate_generated_code_with_valid_python(self):
        """validate_generated_code should return True for valid Python."""
        code = "class Test:\n    pass"
        assert validate_generated_code(code) is True

    def test_validate_generated_code_with_invalid_python(self):
        """validate_generated_code should raise SyntaxError for invalid Python."""
        code = "class Test\n    pass"  # Missing colon
        with pytest.raises(SyntaxError):
            validate_generated_code(code)
