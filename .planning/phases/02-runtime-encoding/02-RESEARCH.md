# Phase 2: Runtime Encoding - Research

**Researched:** 2026-02-19
**Domain:** Binary encoding/decoding with bitwise operations and runtime validation
**Confidence:** HIGH

## Summary

Phase 2 implements the runtime encoding and decoding engine that transforms Python dictionaries to 64-bit integers and back. The standard approach uses Python's built-in bitwise operators (<<, >>, &, |) for bit manipulation, explicit validation before encoding to prevent silent corruption, and comprehensive round-trip testing with property-based tests using Hypothesis. The architecture follows an encoder/decoder pattern with separate concerns: validation happens first, then bit packing/unpacking uses precomputed layouts from Phase 1.

**Key insight:** Bit-level encoding is mathematically deterministic - given a schema and data, there's exactly one correct encoding. The challenge is fail-fast validation (catching constraint violations before bit operations) and correct handling of edge cases (signed integers, nullable fields with presence bits, endianness). Python's unlimited-precision integers eliminate overflow concerns during computation, but we must validate that final values fit in 64 bits.

**Primary recommendation:** Use bitwise operators directly (don't use struct module for bit-level packing), validate all constraints at encode time with clear error messages, implement encoding as bit packing into accumulator starting from LSB, implement decoding as bit extraction using masks at computed offsets, and test round-trip correctness with Hypothesis property-based tests for all field type combinations.

## Standard Stack

The established libraries/tools for binary encoding and runtime validation in Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python bitwise ops | Built-in | Bit manipulation (<<, >>, &, \|, ^, ~) | Native CPU instructions, fastest possible, no dependencies, works on arbitrary-precision integers |
| Pydantic v2 | 2.12.5+ | Runtime validation | Already used in Phase 1, provides field validators and model validators, 5-50x faster than v1 with Rust core |
| Python int methods | Built-in | bit_length(), to_bytes(), from_bytes() | Standard methods for bit width calculation and integer/bytes conversion, handles endianness |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hypothesis | 6.151.9+ | Property-based testing | Critical for round-trip testing (encode→decode→encode invariant), auto-generates edge cases, already in Phase 1 dependencies |
| pytest | 9.0.2+ | Test framework | Already used in Phase 1, provides parametrize for testing all field type combinations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bitwise ops | struct.pack/unpack | struct operates on bytes not bits, requires byte alignment, less control over exact bit layout |
| Bitwise ops | bitstruct library | External dependency (8.17.0 on PyPI), adds complexity when built-in operators suffice for our use case |
| Manual validation | Pydantic validation | Pydantic already integrated from Phase 1, provides clear error messages, avoid reinventing validation |
| Hypothesis | Manual edge case tests | Hypothesis automatically finds edge cases we'd miss, standard for round-trip testing |

**Installation:**
```bash
# Core dependencies already installed from Phase 1
pip install pydantic>=2.12.5
pip install pytest>=9.0.2 hypothesis>=6.151.9  # dev dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
bitschema/
├── encoder.py         # Encode dict → int64 using schema
├── decoder.py         # Decode int64 → dict using schema
├── validator.py       # Runtime value validation (extends Phase 1)
├── bitops.py          # Bit manipulation helpers (masks, shifts)
└── errors.py          # Encoding/decoding exceptions (extends Phase 1)
```

### Pattern 1: Bit-Packing Encoder (LSB-first)
**What:** Encode fields into 64-bit integer by packing bits from LSB (offset 0) upward
**When to use:** Always for encoding - deterministic and matches layout computation from Phase 1

**Example:**
```python
# Source: Python bitwise operators + BitSchema layout
def encode(data: dict, layouts: list[FieldLayout]) -> int:
    """
    Encode dictionary to 64-bit integer using field layouts.

    Algorithm:
    1. Initialize accumulator = 0
    2. For each field in layout order:
       a. Validate value against constraints
       b. Normalize value to unsigned representation
       c. Create bit mask for field width
       d. Shift value to field offset
       e. OR into accumulator
    3. Return accumulator

    Example:
        layouts = [
            FieldLayout(name="active", type="bool", offset=0, bits=1, constraints={}),
            FieldLayout(name="age", type="int", offset=1, bits=7, constraints={"min": 0, "max": 127})
        ]
        data = {"active": True, "age": 42}

        # Step 1: active = 1, offset = 0, bits = 1
        # mask = (1 << 1) - 1 = 0b1
        # value = 1 & 0b1 = 1
        # accumulator |= (1 << 0) = 0b1

        # Step 2: age = 42, offset = 1, bits = 7
        # mask = (1 << 7) - 1 = 0b1111111
        # value = 42 & 0b1111111 = 42
        # accumulator |= (42 << 1) = 0b1010101

        # Result: 0b1010101 = 85
    """
    accumulator = 0

    for layout in layouts:
        # Get value from data dict
        value = data[layout.name]

        # Validate against constraints (TYPE-05, ENCODE-02, ENCODE-03, ENCODE-04)
        validate_field_value(value, layout)

        # Normalize to unsigned representation
        if layout.type == "bool":
            normalized = 1 if value else 0
        elif layout.type == "int":
            # Convert signed to unsigned by subtracting min
            min_value = layout.constraints.get("min", 0)
            normalized = value - min_value
        elif layout.type == "enum":
            # Convert enum value to index
            normalized = layout.constraints["values"].index(value)

        # Create mask for field width (prevents overflow)
        mask = (1 << layout.bits) - 1

        # Pack into accumulator at offset
        accumulator |= ((normalized & mask) << layout.offset)

    return accumulator
```

### Pattern 2: Bit-Unpacking Decoder
**What:** Decode 64-bit integer to dictionary by extracting bits at computed offsets
**When to use:** Always for decoding - inverse of encoding

**Example:**
```python
# Source: Python bitwise operators + BitSchema layout
def decode(encoded: int, layouts: list[FieldLayout]) -> dict:
    """
    Decode 64-bit integer to dictionary using field layouts.

    Algorithm:
    1. Initialize empty result dict
    2. For each field in layout order:
       a. Create bit mask for field width
       b. Shift encoded value right by offset
       c. AND with mask to extract bits
       d. Denormalize to semantic value
       e. Store in result dict
    3. Return result dict

    Example:
        encoded = 85 (0b1010101)
        layouts = [same as encode example]

        # Step 1: active at offset=0, bits=1
        # mask = (1 << 1) - 1 = 0b1
        # extracted = (85 >> 0) & 0b1 = 1
        # value = bool(1) = True

        # Step 2: age at offset=1, bits=7
        # mask = (1 << 7) - 1 = 0b1111111
        # extracted = (85 >> 1) & 0b1111111 = 42
        # value = 42 + 0 (min) = 42

        # Result: {"active": True, "age": 42}
    """
    result = {}

    for layout in layouts:
        # Create mask for field width
        mask = (1 << layout.bits) - 1

        # Extract bits at offset (DECODE-02)
        extracted = (encoded >> layout.offset) & mask

        # Denormalize to semantic value (DECODE-03)
        if layout.type == "bool":
            value = bool(extracted)
        elif layout.type == "int":
            # Convert unsigned back to signed by adding min
            min_value = layout.constraints.get("min", 0)
            value = extracted + min_value
        elif layout.type == "enum":
            # Convert index back to enum value
            value = layout.constraints["values"][extracted]

        result[layout.name] = value

    return result
```

### Pattern 3: Nullable Fields with Presence Bits
**What:** Encode nullable fields using presence bit (1 = value present, 0 = None)
**When to use:** When field has nullable=True in schema (TYPE-06)

**Example:**
```python
# Source: BitSchema nullable design + binary encoding patterns
def encode_nullable_field(value, layout: FieldLayout, accumulator: int, offset: int) -> tuple[int, int]:
    """
    Encode nullable field using presence bit + value bits.

    Layout:
        [presence_bit][value_bits]

    Examples:
        Field: nullable int, 7 bits, offset 0
        - Value = 42: 0b10101010 (presence=1, value=42)
        - Value = None: 0b00000000 (presence=0, value=ignored)

    Returns:
        (updated_accumulator, bits_used)
    """
    presence_offset = offset
    value_offset = offset + 1  # Value starts after presence bit

    if value is None:
        # Presence bit = 0, value bits = 0 (ENCODE-06, DECODE-04)
        # No-op: accumulator already has zeros at this position
        return accumulator, layout.bits + 1
    else:
        # Presence bit = 1
        accumulator |= (1 << presence_offset)

        # Encode value bits (same as non-nullable)
        normalized = normalize_value(value, layout)
        mask = (1 << layout.bits) - 1
        accumulator |= ((normalized & mask) << value_offset)

        return accumulator, layout.bits + 1

def decode_nullable_field(encoded: int, layout: FieldLayout, offset: int):
    """
    Decode nullable field by checking presence bit.

    Returns:
        Decoded value or None
    """
    presence_offset = offset
    value_offset = offset + 1

    # Check presence bit
    presence = (encoded >> presence_offset) & 1

    if presence == 0:
        return None  # DECODE-04
    else:
        # Extract and denormalize value
        mask = (1 << layout.bits) - 1
        extracted = (encoded >> value_offset) & mask
        return denormalize_value(extracted, layout)
```

### Pattern 4: Fail-Fast Validation at Encode Time
**What:** Validate all constraints before any bit packing occurs
**When to use:** Always at encode time - prevents silent corruption (ENCODE-02, ENCODE-03, ENCODE-04)

**Example:**
```python
# Source: Pydantic validation + BitSchema requirements
from .errors import ValidationError

def validate_field_value(value, layout: FieldLayout) -> None:
    """
    Validate field value against schema constraints.
    Raises ValidationError with field name, value, and violated constraint.

    Validates:
    - ENCODE-02: Required fields present
    - ENCODE-03: Values within constraints
    - TYPE-05: Values fit in bit width
    """
    field_name = layout.name

    # Check for None on non-nullable field
    if value is None and not getattr(layout, 'nullable', False):
        raise ValidationError(
            field_name=field_name,
            message=f"Field '{field_name}' is not nullable but received None"
        )

    if value is None:
        return  # Nullable field with None is valid

    # Type-specific validation
    if layout.type == "bool":
        if not isinstance(value, bool):
            raise ValidationError(
                field_name=field_name,
                message=f"Field '{field_name}' expects bool, got {type(value).__name__}"
            )

    elif layout.type == "int":
        if not isinstance(value, int):
            raise ValidationError(
                field_name=field_name,
                message=f"Field '{field_name}' expects int, got {type(value).__name__}"
            )

        min_value = layout.constraints.get("min")
        max_value = layout.constraints.get("max")

        if min_value is not None and value < min_value:
            raise ValidationError(
                field_name=field_name,
                message=f"Field '{field_name}' value {value} is below minimum {min_value}"
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                field_name=field_name,
                message=f"Field '{field_name}' value {value} exceeds maximum {max_value}"
            )

    elif layout.type == "enum":
        allowed_values = layout.constraints["values"]
        if value not in allowed_values:
            raise ValidationError(
                field_name=field_name,
                message=f"Field '{field_name}' value '{value}' not in allowed values: {allowed_values}"
            )
```

### Pattern 5: Round-Trip Testing with Hypothesis
**What:** Property-based tests that verify encode(decode(x)) == x for all field types
**When to use:** Always - critical requirement DECODE-05

**Example:**
```python
# Source: Hypothesis documentation + round-trip testing patterns
from hypothesis import given, strategies as st
import pytest

def generate_valid_value(layout: FieldLayout):
    """Generate Hypothesis strategy for valid field values."""
    if layout.type == "bool":
        return st.booleans()
    elif layout.type == "int":
        min_val = layout.constraints.get("min", 0)
        max_val = layout.constraints.get("max", 2**layout.bits - 1)
        return st.integers(min_value=min_val, max_value=max_val)
    elif layout.type == "enum":
        return st.sampled_from(layout.constraints["values"])

@given(st.data())
def test_round_trip_correctness(data):
    """
    Property: For all valid inputs, decode(encode(x)) == x

    This is the fundamental invariant of any encoding system.
    """
    # Generate schema
    schema = data.draw(generate_schema())
    layouts, total_bits = compute_bit_layout(schema.fields)

    # Generate valid data for schema
    input_data = {}
    for layout in layouts:
        value = data.draw(generate_valid_value(layout))
        input_data[layout.name] = value

    # Encode then decode
    encoded = encode(input_data, layouts)
    decoded = decode(encoded, layouts)

    # Verify round-trip correctness (DECODE-05)
    assert decoded == input_data, f"Round-trip failed: {input_data} -> {encoded} -> {decoded}"

@given(st.integers(min_value=0, max_value=127), st.booleans())
def test_individual_field_round_trip(age_value, active_value):
    """Test round-trip for specific field combination."""
    layouts = [
        FieldLayout(name="age", type="int", offset=0, bits=7, constraints={"min": 0, "max": 127}),
        FieldLayout(name="active", type="bool", offset=7, bits=1, constraints={})
    ]

    original = {"age": age_value, "active": active_value}
    encoded = encode(original, layouts)
    decoded = decode(encoded, layouts)

    assert decoded == original
```

### Anti-Patterns to Avoid

- **Don't use struct.pack/unpack**: Works on bytes not bits, requires byte alignment, loses control over exact bit positions
- **Don't skip encode-time validation**: Leads to silent corruption, makes debugging impossible (see Pitfall 9)
- **Don't assume Python int overflow**: Python ints are unlimited precision, but 64-bit constraint must be validated explicitly
- **Don't use right shift on signed integers without care**: Python's arithmetic right shift preserves sign, which is correct but can surprise when expecting logical shift
- **Don't hard-code bit widths**: Use layout.bits from schema, not magic numbers like 8 or 16
- **Don't mask before validating**: Validate raw value first, then mask during packing (masking hides constraint violations)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bit mask generation | Manual (1 << n) - 1 with bugs | Helper function: create_mask(bits) | Edge cases like 0 bits or 64 bits need special handling |
| Signed/unsigned conversion | Manual two's complement math | Use value - min for normalization | Handles negative ranges correctly, avoids bit width confusion |
| Field validation | Manual type checks and if statements | Pydantic validators or dedicated validate_field_value() | Provides clear error messages, reusable, testable |
| Round-trip test generation | Manual test cases for each type | Hypothesis property-based tests | Finds edge cases automatically (boundary values, combinations) |
| Endianness conversion | Manual byte swapping | int.to_bytes(byteorder='big') | Handles platform differences, tested by Python core team |

**Key insight:** Bit manipulation is straightforward in Python (bitwise operators are built-in and fast), but validation and testing require discipline. Use Hypothesis for round-trip tests - it will find edge cases (max value, min value, 0, None) that manual tests miss.

## Common Pitfalls

### Pitfall 1: Forgetting to Validate Before Encoding
**What goes wrong:** Invalid values (exceeding max, below min, wrong type) are encoded silently, causing corruption detected only at decode time or in production.

**Why it happens:** Developers focus on bit math and forget validation. Performance pressure leads to skipping "slow" validation. Testing only with valid data doesn't catch missing validation.

**How to avoid:**
- Validate ALL fields before any bit operations (ENCODE-02, ENCODE-03, ENCODE-04)
- Use dedicated validation function that runs before encode
- Test validation explicitly: `pytest.raises(ValidationError, encode, {"age": 256})`
- Include field name, value, and constraint in error message

**Warning signs:**
- Encode succeeds but decode produces wrong values
- Production data corruption from user input
- Different behavior between test and production data

### Pitfall 2: Incorrect Signed Integer Handling
**What goes wrong:** Using raw value in bit operations for signed integers produces wrong results. Example: encoding -5 with 4 bits should work if range is [-8, 7], but direct bit packing of -5 (0xFFFFFFFB in two's complement) overflows.

**Why it happens:** Confusing two's complement representation with bit packing. Assuming bit operations work on signed values. Not normalizing to unsigned before packing.

**How to avoid:**
```python
# WRONG: Direct bit packing of signed value
value = -5
packed = value & ((1 << 4) - 1)  # 0xFB (wrong!)

# CORRECT: Normalize to unsigned by subtracting min
min_value = -8
max_value = 7
value = -5
normalized = value - min_value  # -5 - (-8) = 3
packed = normalized & ((1 << 4) - 1)  # 3 (correct!)

# On decode:
extracted = 3
denormalized = extracted + min_value  # 3 + (-8) = -5 ✓
```

**Warning signs:**
- Signed integer fields fail to round-trip
- Negative values produce huge positive values
- Min/max validation passes but encoding fails

### Pitfall 3: Off-by-One in Bit Masks
**What goes wrong:** Using `1 << bits` instead of `(1 << bits) - 1` for mask, or using `bits - 1` instead of `bits` in mask calculation. Example: For 8 bits, mask should be 0xFF (255), not 0x100 (256).

**Why it happens:** Confusing bit width with bit value. Forgetting that mask needs all 1s, not 1 followed by 0s.

**How to avoid:**
```python
# WRONG: Mask is power of 2, not all ones
mask = 1 << 8  # 0x100 = 256 (wrong!)

# CORRECT: Mask is (2^n - 1) to get all ones
mask = (1 << 8) - 1  # 0xFF = 255 (correct!)

# Helper function prevents mistakes
def create_mask(bits: int) -> int:
    """Create bit mask with <bits> ones."""
    if bits == 0:
        return 0
    if bits >= 64:
        return (1 << 64) - 1  # Python handles this correctly
    return (1 << bits) - 1
```

**Warning signs:**
- Values are off by 1 after round-trip
- Mask validation tests fail
- Extracting field gets 1 extra bit

### Pitfall 4: Missing Required Fields Not Detected
**What goes wrong:** Encoding dict with missing required fields causes KeyError at bit packing time, with unclear error message about field name rather than constraint violation.

**Why it happens:** Not checking dict.keys() against schema before accessing values. Assuming user provides all fields.

**How to avoid:**
```python
# Validate all required fields present (ENCODE-02)
def validate_all_fields_present(data: dict, layouts: list[FieldLayout]) -> None:
    """Ensure all required fields are in data dict."""
    required_fields = {layout.name for layout in layouts if not getattr(layout, 'nullable', False)}
    provided_fields = set(data.keys())

    missing = required_fields - provided_fields
    if missing:
        raise ValidationError(
            field_name=None,
            message=f"Missing required fields: {sorted(missing)}"
        )

    # Also check for extra fields (optional: warn or error)
    extra = provided_fields - {layout.name for layout in layouts}
    if extra:
        # Could warn or error depending on strictness
        pass
```

**Warning signs:**
- KeyError instead of ValidationError
- Unclear error messages about missing keys
- Crashes in production from incomplete user input

### Pitfall 5: Nullable Field Presence Bit Confusion
**What goes wrong:** Forgetting that nullable fields use 1 extra bit for presence, or encoding None as 0 without presence bit (loses distinction between None and 0 value).

**Why it happens:** Not accounting for presence bit in offset calculation. Treating None as "zero value" instead of "absent value".

**How to avoid:**
- Always add 1 to bits for nullable fields in layout computation (done in Phase 1)
- Use separate presence bit at field offset, value bits start at offset+1
- Encode None as presence=0, any value as presence=1 + normalized_value
- Test None explicitly: `assert decode(..., {"score": None}) == {"score": None}`
- Verify bit count includes presence bit: nullable int(7 bits) = 8 bits total

**Warning signs:**
- Nullable fields overlap with next field
- None decodes as 0 or minimum value
- Round-trip fails for None values

## Code Examples

Verified patterns from Python documentation and BitSchema requirements:

### Complete Encoder Implementation
```python
# Source: BitSchema requirements + Python bitwise operators
from typing import Any
from .layout import FieldLayout
from .errors import ValidationError

def encode(data: dict[str, Any], layouts: list[FieldLayout]) -> int:
    """
    Encode Python dict to 64-bit integer using schema layouts.

    Implements:
    - ENCODE-01: Encode dict to int using schema
    - ENCODE-02: Validate required fields present
    - ENCODE-03: Validate values within constraints
    - ENCODE-04: Fail fast with clear errors
    - ENCODE-05: Platform-independent (Python int is platform-independent)
    - ENCODE-06: Handle nullable fields with presence bit

    Returns:
        64-bit integer with packed fields

    Raises:
        ValidationError: If validation fails (missing field, constraint violation)
    """
    # Validate all required fields present (ENCODE-02)
    validate_all_fields_present(data, layouts)

    accumulator = 0
    current_offset = 0

    for layout in layouts:
        value = data.get(layout.name)

        # Handle nullable fields (ENCODE-06)
        if layout.nullable:
            if value is None:
                # Presence bit = 0, skip value bits
                current_offset += 1 + layout.bits
                continue
            else:
                # Presence bit = 1
                accumulator |= (1 << current_offset)
                current_offset += 1

        # Validate value (ENCODE-03, ENCODE-04)
        validate_field_value(value, layout)

        # Normalize to unsigned
        normalized = normalize_value(value, layout)

        # Pack into accumulator
        mask = (1 << layout.bits) - 1
        accumulator |= ((normalized & mask) << current_offset)
        current_offset += layout.bits

    # Validate total fits in 64 bits (redundant with Phase 1, but defensive)
    if current_offset > 64:
        raise ValidationError(
            field_name=None,
            message=f"Encoded value uses {current_offset} bits, exceeds 64-bit limit"
        )

    return accumulator

def normalize_value(value: Any, layout: FieldLayout) -> int:
    """Convert semantic value to unsigned integer for bit packing."""
    if layout.type == "bool":
        return 1 if value else 0
    elif layout.type == "int":
        min_value = layout.constraints.get("min", 0)
        return value - min_value
    elif layout.type == "enum":
        return layout.constraints["values"].index(value)
    else:
        raise ValueError(f"Unknown field type: {layout.type}")
```

### Complete Decoder Implementation
```python
# Source: BitSchema requirements + Python bitwise operators
def decode(encoded: int, layouts: list[FieldLayout]) -> dict[str, Any]:
    """
    Decode 64-bit integer to Python dict using schema layouts.

    Implements:
    - DECODE-01: Decode int to dict using schema
    - DECODE-02: Extract fields using bit masks at offsets
    - DECODE-03: Convert raw bits to semantic values
    - DECODE-04: Decode nullable fields correctly (None when presence=0)
    - DECODE-05: Round-trip correctness (tested separately)

    Returns:
        Dictionary with decoded field values
    """
    result = {}
    current_offset = 0

    for layout in layouts:
        # Handle nullable fields (DECODE-04)
        if layout.nullable:
            presence = (encoded >> current_offset) & 1
            current_offset += 1

            if presence == 0:
                result[layout.name] = None
                current_offset += layout.bits
                continue

        # Extract bits at offset (DECODE-02)
        mask = (1 << layout.bits) - 1
        extracted = (encoded >> current_offset) & mask
        current_offset += layout.bits

        # Denormalize to semantic value (DECODE-03)
        value = denormalize_value(extracted, layout)
        result[layout.name] = value

    return result

def denormalize_value(extracted: int, layout: FieldLayout) -> Any:
    """Convert unsigned integer to semantic value."""
    if layout.type == "bool":
        return bool(extracted)
    elif layout.type == "int":
        min_value = layout.constraints.get("min", 0)
        return extracted + min_value
    elif layout.type == "enum":
        return layout.constraints["values"][extracted]
    else:
        raise ValueError(f"Unknown field type: {layout.type}")
```

### Comprehensive Validation
```python
# Source: Pydantic patterns + BitSchema requirements
class EncodingError(Exception):
    """Raised when encoding fails validation."""
    def __init__(self, field_name: str | None, message: str):
        self.field_name = field_name
        super().__init__(message if field_name is None else f"Field '{field_name}': {message}")

def validate_all_fields_present(data: dict, layouts: list[FieldLayout]) -> None:
    """Validate all required fields are present (ENCODE-02)."""
    required = {layout.name for layout in layouts}
    provided = set(data.keys())
    missing = required - provided

    if missing:
        raise EncodingError(None, f"Missing required fields: {sorted(missing)}")

def validate_field_value(value: Any, layout: FieldLayout) -> None:
    """
    Validate field value against constraints (ENCODE-03, ENCODE-04).

    Provides clear error messages with field name, value, and violated constraint.
    """
    if layout.type == "bool":
        if not isinstance(value, bool):
            raise EncodingError(
                layout.name,
                f"Expected bool, got {type(value).__name__}"
            )

    elif layout.type == "int":
        if not isinstance(value, int):
            raise EncodingError(
                layout.name,
                f"Expected int, got {type(value).__name__}"
            )

        min_val = layout.constraints.get("min")
        max_val = layout.constraints.get("max")

        if min_val is not None and value < min_val:
            raise EncodingError(
                layout.name,
                f"Value {value} below minimum {min_val}"
            )

        if max_val is not None and value > max_val:
            raise EncodingError(
                layout.name,
                f"Value {value} exceeds maximum {max_val}"
            )

    elif layout.type == "enum":
        values = layout.constraints["values"]
        if value not in values:
            raise EncodingError(
                layout.name,
                f"Value '{value}' not in allowed values: {values}"
            )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| struct.pack/unpack for binary data | Direct bitwise operators for bit-level packing | Always available in Python | More control, works at bit granularity not byte granularity |
| Manual validation with if statements | Pydantic v2 validators | Pydantic v2 (2023) | 5-50x faster, clear error messages, reusable validators |
| Manual round-trip tests | Hypothesis property-based tests | Hypothesis mature since 2015 | Finds edge cases automatically, reduces test code |
| Platform-specific endianness | Explicit byteorder parameter | Python 3.2+ (int.to_bytes) | Cross-platform compatibility, clear intent |
| Silent overflow/truncation | Explicit validation before packing | Modern practice | Fail-fast prevents data corruption |

**Deprecated/outdated:**
- Using struct for bit-level packing: Works on bytes, not bits; use bitwise operators
- Skipping encode-time validation: Modern systems validate early and fail fast
- Assuming 32-bit int: Python int is arbitrary precision; validate bit width explicitly

## Open Questions

Things that couldn't be fully resolved:

1. **Endianness for multi-byte export**
   - What we know: Python int operations are platform-independent, endianness only matters for to_bytes/from_bytes
   - What's unclear: Should Phase 2 support to_bytes export, or just keep as int?
   - Recommendation: Keep as int in Phase 2, add to_bytes in Phase 3 with explicit byteorder parameter

2. **Performance optimization opportunities**
   - What we know: Python bitwise ops are fast, but validation has overhead
   - What's unclear: Should we provide "unsafe" encode variant that skips validation?
   - Recommendation: Always validate in Phase 2, defer unsafe variant to Phase 4 if needed

3. **Nullable vs Optional distinction**
   - What we know: BitSchema treats nullable as "field always present, value may be None"
   - What's unclear: Should we support "optional" (field may be omitted from dict)?
   - Recommendation: Phase 2 implements nullable only (TYPE-06), defer optional to later phase

## Sources

### Primary (HIGH confidence)
- [Python Built-in Types - Bitwise Operations](https://docs.python.org/3/library/stdtypes.html) - Official docs, Feb 19 2026
- [Bitwise Operators in Python – Real Python](https://realpython.com/python-bitwise-operators/) - Comprehensive guide to Python bitwise operations
- [Pydantic Documentation - Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Field validation patterns
- [Hypothesis - The Encode/Decode Invariant](https://hypothesis.works/articles/encode-decode-invariant/) - Round-trip testing pattern

### Secondary (MEDIUM confidence)
- [Python Bit Manipulation and Masking Techniques - AskPython](https://www.askpython.com/python/examples/python-bit-manipulation-masking-techniques) - Practical examples
- [How to Convert Signed to Unsigned Integers in Python – TheLinuxCode](https://thelinuxcode.com/how-to-convert-signed-to-unsigned-integers-in-python-fixed-width-twos-complement-and-practical-interop/) - Fixed-width integer handling
- [Pydantic: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/pydantic-complete-guide) - Modern Pydantic patterns
- [struct — Interpret bytes as packed binary data](https://docs.python.org/3/library/struct.html) - Alternative (byte-level) approach

### Tertiary (LOW confidence)
- [bitstruct · PyPI](https://pypi.org/project/bitstruct/) - Third-party bit packing library (alternative to built-in approach)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Built-in Python operators, Pydantic already integrated from Phase 1
- Architecture: HIGH - Patterns based on official Python docs and established encode/decode patterns
- Pitfalls: HIGH - Sourced from comprehensive pitfalls research document and domain expertise

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (30 days - stable ecosystem, Python built-ins don't change)
