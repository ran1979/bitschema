# Phase 1: Foundation - Research

**Researched:** 2026-02-19
**Domain:** Schema parsing, validation, and bit layout computation
**Confidence:** HIGH

## Summary

Phase 1 implements the foundational layer: schema parsing, validation, and bit layout computation. The standard approach uses Pydantic for schema validation (leveraging its JSON Schema generation and type-safe validation), PyYAML for YAML parsing with security-conscious `safe_load()`, and Python's built-in `bit_length()` method for computing minimum bit requirements. Code organization follows a functional decomposition with separate modules for parsing, validation, and layout computation.

**Key insight:** Bit layout computation is deterministic mathematical calculation, not a complex algorithm. The critical challenges are fail-fast validation (catching errors before encoding) and clear error messages (helping developers fix schema issues quickly).

**Primary recommendation:** Use Pydantic BaseModel for schema definition, compute bit requirements using integer `bit_length()` with explicit range validation, and organize code into parser → validator → layout_computer pipeline with clear separation of concerns.

## Standard Stack

The established libraries/tools for schema validation and bit computation in Python:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.12.5+ | Schema validation & parsing | Industry standard with Rust-based core (10-80x faster than v1), built-in JSON Schema generation, excellent type hint integration, validated in production by FastAPI and major projects |
| PyYAML | 6.0.3+ | YAML parsing | Most prevalent Python YAML library, complete YAML 1.1 support, Python 3.8-3.14 compatible |
| Python stdlib json | Built-in | JSON parsing | Fast C implementation, no dependencies, sufficient for schema I/O |
| Python stdlib dataclasses | Built-in | Schema modeling | Native support for `__post_init__` validation, frozen instances, automatic method generation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hypothesis | 6.151.9+ | Property-based testing | Critical for bit-packing edge cases (boundary values, overflow scenarios), auto-generates 100 test cases per property by default |
| pytest | 9.0.2+ | Test framework | Standard for Python testing, fixture support, parametrization, auto-discovery |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic | msgspec 0.20+ | msgspec is 10-20x faster but lacks custom validators and JSON Schema generation (needed for OUTPUT-04) |
| Pydantic | attrs + cattrs | Less integrated type hint support, smaller ecosystem, no built-in JSON Schema |
| PyYAML | ruamel.yaml | ruamel preserves formatting (not needed for schema input), heavier dependency |

**Installation:**
```bash
pip install pydantic>=2.12.5 PyYAML>=6.0.3
pip install pytest>=9.0.2 hypothesis>=6.151.9  # dev dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
bitschema/
├── parser.py           # JSON/YAML → Python dict
├── schema.py          # Pydantic models for schema definition
├── validator.py       # Schema validation (uniqueness, bit limits)
├── layout.py          # Bit offset computation
├── types.py           # Field type definitions (BooleanField, IntegerField, etc.)
└── errors.py          # Custom exceptions with context
```

### Pattern 1: Pydantic Schema Definition
**What:** Use Pydantic BaseModel to define the input schema structure with automatic validation
**When to use:** Always for schema parsing - leverages Pydantic's validation and type coercion

**Example:**
```python
# Source: Pydantic docs + BitSchema requirements
from pydantic import BaseModel, Field, field_validator
from typing import Literal

class IntegerField(BaseModel):
    name: str
    type: Literal["integer"]
    min_value: int
    max_value: int

    @field_validator("max_value")
    @classmethod
    def validate_range(cls, max_val: int, info) -> int:
        min_val = info.data.get("min_value")
        if min_val is not None and max_val < min_val:
            raise ValueError(f"max_value {max_val} must be >= min_value {min_val}")
        return max_val

class BooleanField(BaseModel):
    name: str
    type: Literal["boolean"]

class BitSchema(BaseModel):
    version: str = "1.0"
    fields: list[IntegerField | BooleanField]

    @field_validator("fields")
    @classmethod
    def validate_unique_names(cls, fields):
        names = [f.name for f in fields]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate field names: {set(duplicates)}")
        return fields
```

### Pattern 2: Bit Width Calculation
**What:** Use Python's built-in `int.bit_length()` to compute minimum bits required
**When to use:** For all integer range calculations - this is the standard approach

**Example:**
```python
# Source: Python docs + bit-packing best practices
def compute_bits_for_range(min_value: int, max_value: int) -> int:
    """
    Compute minimum bits needed to represent integers in [min_value, max_value].

    For unsigned (min >= 0): bits = max_value.bit_length()
    For signed: need to represent range, not just max value.

    Examples:
        [0, 1] → 1 bit (boolean)
        [0, 255] → 8 bits
        [0, 256] → 9 bits
        [-128, 127] → 8 bits (two's complement)
    """
    if min_value < 0:
        # Signed integer: compute range size and add sign bit
        range_size = max_value - min_value
        return range_size.bit_length()
    else:
        # Unsigned integer: just need to fit max value
        return max_value.bit_length()
```

### Pattern 3: Fail-Fast Validation Pipeline
**What:** Separate validation into stages that fail immediately with context
**When to use:** Always - validates requirements early, provides clear errors

**Example:**
```python
# Source: Validation best practices + BitSchema requirements
from typing import NamedTuple

class ValidationError(Exception):
    """Schema validation error with context."""
    def __init__(self, message: str, field_name: str | None = None):
        self.field_name = field_name
        super().__init__(f"Field '{field_name}': {message}" if field_name else message)

class BitLayout(NamedTuple):
    offset: int
    bits: int

def validate_and_compute_layout(schema: BitSchema) -> dict[str, BitLayout]:
    """
    Validate schema and compute bit layout.
    Fails fast with clear errors.
    """
    # Stage 1: Field-level validation (already done by Pydantic)

    # Stage 2: Compute bit requirements
    layouts = {}
    offset = 0

    for field in schema.fields:
        if field.type == "boolean":
            bits = 1
        elif field.type == "integer":
            bits = compute_bits_for_range(field.min_value, field.max_value)
        else:
            raise ValidationError(f"Unknown field type: {field.type}", field.name)

        layouts[field.name] = BitLayout(offset=offset, bits=bits)
        offset += bits

    # Stage 3: 64-bit limit validation (LAYOUT-05)
    if offset > 64:
        raise ValidationError(
            f"Schema exceeds 64-bit limit: {offset} bits required "
            f"({offset - 64} bits over). Breakdown: " +
            ", ".join(f"{name}={layout.bits}bits" for name, layout in layouts.items())
        )

    return layouts
```

### Pattern 4: Safe YAML Parsing
**What:** Always use `yaml.safe_load()` to prevent code execution vulnerabilities
**When to use:** Every time parsing YAML input (SCHEMA-02)

**Example:**
```python
# Source: PyYAML security documentation
import yaml
from pathlib import Path

def load_schema_file(file_path: Path) -> dict:
    """
    Load schema from JSON or YAML file.
    Uses safe_load() to prevent arbitrary code execution.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix in ['.yaml', '.yml']:
            # CRITICAL: Use safe_load(), NOT load()
            # yaml.load() can execute arbitrary Python code
            data = yaml.safe_load(f)
        elif file_path.suffix == '.json':
            import json
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    if not isinstance(data, dict):
        raise ValueError(f"Schema must be object/dict, got {type(data).__name__}")

    return data
```

### Anti-Patterns to Avoid

- **Don't use `yaml.load()`**: Security vulnerability - can execute arbitrary code. Always use `yaml.safe_load()`
- **Don't compute bits with math.log2()**: Floating point precision issues. Use `int.bit_length()` instead
- **Don't skip encode-time validation**: Validates only at decode time leads to silent corruption
- **Don't use generic error messages**: "Validation failed" → Include field name, value, constraint
- **Don't hand-roll bit width calculations**: `bit_length()` is standard and correct for unsigned integers

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Computing bits for integer range | Manual math with log2 or bit counting | `int.bit_length()` | Python built-in handles edge cases correctly (0, negative, powers of 2) |
| Schema validation with type checking | Manual `isinstance()` checks | Pydantic BaseModel | Handles type coercion, nested validation, clear error messages automatically |
| JSON Schema generation | Manual dict construction | `pydantic.BaseModel.model_json_schema()` | Outputs standard JSON Schema format, handles all type mappings |
| Parsing YAML securely | Custom YAML parser or `yaml.load()` | `yaml.safe_load()` | Prevents code execution vulnerabilities, standard secure approach |
| Error context (field name, value) | String formatting in raise statements | Custom exception classes with attributes | Enables programmatic error handling, structured error reporting |

**Key insight:** Phase 1 is 90% validation logic, 10% computation. Don't reinvent validation - Pydantic handles the hard parts (type checking, nested structures, clear errors). Focus on domain-specific validation (bit limits, field uniqueness).

## Common Pitfalls

### Pitfall 1: Silent Integer Overflow in Bit Calculations
**What goes wrong:** Forgetting to validate that computed bit width fits in 64-bit limit, or that integer values fit in computed bits. Results in silent truncation or runtime errors.

**Why it happens:** Validation happens at different stages (schema validation vs encode-time), easy to miss one path. Integer bit_length() doesn't validate ranges.

**How to avoid:**
- Validate total bits ≤ 64 after computing layout (LAYOUT-05)
- Validate min/max values fit in computed bits (TYPE-05)
- Provide clear error: "Value 256 requires 9 bits but field allocated 8 bits"
- Test boundary cases: max value, max+1, min value, min-1

**Warning signs:**
- Tests pass with small numbers but fail with large values
- Different behavior between test and production data
- Mysterious "value too large" errors without context

### Pitfall 2: Incorrect Bit Width for Signed Integers
**What goes wrong:** Using `max_value.bit_length()` for signed integers gives wrong result. Need to compute range size, not just max magnitude.

**Why it happens:** Confusing unsigned (absolute value) with signed (range-based) bit requirements. Two's complement representation requires different calculation.

**How to avoid:**
```python
# WRONG: Only works for unsigned
bits = max_value.bit_length()  # [-128, 127] → 7 bits (WRONG, need 8)

# CORRECT: Compute range size
range_size = max_value - min_value  # 127 - (-128) = 255
bits = range_size.bit_length()  # 255 → 8 bits ✓
```

**Warning signs:**
- Signed integer fields failing to encode valid values
- Off-by-one errors in bit allocation
- Different results for positive vs negative ranges

### Pitfall 3: YAML Security with yaml.load()
**What goes wrong:** Using `yaml.load()` instead of `yaml.safe_load()` allows arbitrary Python code execution. Attacker-controlled YAML can run system commands.

**Why it happens:** `yaml.load()` is the first example in old tutorials. Looks simpler (no "safe" prefix).

**How to avoid:**
- ALWAYS use `yaml.safe_load()` for untrusted input
- Add linter rule to catch `yaml.load()` usage
- Document security rationale in code comments

**Warning signs:**
- Security scanner warnings about YAML deserialization
- Ability to execute code via crafted YAML files

### Pitfall 4: Field Name Uniqueness Not Validated
**What goes wrong:** Duplicate field names in schema cause fields to overwrite each other in layout dict, losing data silently.

**Why it happens:** Easy to forget when parsing list of fields. No automatic duplicate detection.

**How to avoid:**
- Use Pydantic `@field_validator` to check uniqueness (SCHEMA-04)
- Fail fast with clear message: "Duplicate field names: age, status"
- Include in unit tests: schema with duplicate names should raise error

**Warning signs:**
- Fewer fields in output than input
- Last field with duplicate name "wins"
- Silent data loss during encoding

### Pitfall 5: Off-by-One in Bit Offset Calculation
**What goes wrong:** Using `offset += bits` after field vs before field leads to overlap or gaps. Mixing inclusive/exclusive boundaries.

**Why it happens:** Classic fencepost problem - confusing counting posts vs gaps.

**How to avoid:**
- Use consistent pattern: compute bits, assign offset, increment offset
- Test with 0 bits, 1 bit, 7 bits, 8 bits, 64 bits explicitly
- Validate no overlaps: assert next_offset == prev_offset + prev_bits
- Use NamedTuple or dataclass for layout to prevent typos

**Warning signs:**
- Fields overwriting each other
- Total bits not matching sum of field bits
- Last field offset incorrect

## Code Examples

Verified patterns from official sources:

### Complete Schema Parsing Pipeline
```python
# Source: Pydantic docs + BitSchema requirements
from pathlib import Path
import json
import yaml
from pydantic import BaseModel, Field, field_validator
from typing import Literal

# Schema models (Pydantic)
class BooleanField(BaseModel):
    name: str
    type: Literal["boolean"]

class IntegerField(BaseModel):
    name: str
    type: Literal["integer"]
    min_value: int
    max_value: int

    @field_validator("max_value")
    @classmethod
    def validate_range(cls, v, info):
        if v < info.data.get("min_value", 0):
            raise ValueError("max_value must be >= min_value")
        return v

class EnumField(BaseModel):
    name: str
    type: Literal["enum"]
    values: list[str]

    @field_validator("values")
    @classmethod
    def validate_nonempty(cls, v):
        if len(v) == 0:
            raise ValueError("enum must have at least one value")
        if len(v) != len(set(v)):
            raise ValueError("enum values must be unique")
        return v

FieldType = BooleanField | IntegerField | EnumField

class BitSchema(BaseModel):
    version: str = "1.0"
    fields: list[FieldType]

    @field_validator("fields")
    @classmethod
    def validate_unique_names(cls, fields):
        names = [f.name for f in fields]
        duplicates = [n for n in set(names) if names.count(n) > 1]
        if duplicates:
            raise ValueError(f"Duplicate field names: {duplicates}")
        return fields

# Parser
def parse_schema_file(file_path: Path) -> BitSchema:
    """Parse schema from JSON or YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix in ['.yaml', '.yml']:
            data = yaml.safe_load(f)  # SECURITY: safe_load only
        else:
            data = json.load(f)

    return BitSchema(**data)  # Pydantic validates automatically
```

### Bit Layout Computation
```python
# Source: Python docs + bit-packing patterns
from typing import NamedTuple

class FieldLayout(NamedTuple):
    name: str
    type: str
    offset: int
    bits: int
    constraints: dict

def compute_bit_layout(schema: BitSchema) -> tuple[list[FieldLayout], int]:
    """
    Compute deterministic bit offsets for all fields.
    Returns (layouts, total_bits).

    Validates:
    - TYPE-04: Computes minimum required bits per field
    - LAYOUT-01: Deterministic offsets
    - LAYOUT-02: Fields in declared order
    - LAYOUT-03: No overlaps (implicit via sequential assignment)
    - LAYOUT-04: Total bit count
    - LAYOUT-05: ≤ 64-bit limit
    """
    layouts = []
    offset = 0

    for field in schema.fields:
        # Compute bits required (TYPE-04)
        if isinstance(field, BooleanField):
            bits = 1
            constraints = {}
        elif isinstance(field, IntegerField):
            # Handle signed ranges correctly
            range_size = field.max_value - field.min_value
            bits = range_size.bit_length()
            constraints = {"min": field.min_value, "max": field.max_value}
        elif isinstance(field, EnumField):
            # Enum encoded as index (0..n-1)
            bits = (len(field.values) - 1).bit_length()
            constraints = {"values": field.values}

        # Assign offset (LAYOUT-01, LAYOUT-02)
        layouts.append(FieldLayout(
            name=field.name,
            type=field.type,
            offset=offset,
            bits=bits,
            constraints=constraints
        ))
        offset += bits

    # Validate 64-bit limit (LAYOUT-05)
    if offset > 64:
        breakdown = ", ".join(f"{l.name}={l.bits}" for l in layouts)
        raise ValueError(
            f"Schema exceeds 64-bit limit: {offset} bits total. "
            f"Breakdown: {breakdown}"
        )

    return layouts, offset
```

### JSON Schema Output
```python
# Source: BitSchema OUTPUT requirements
def generate_output_schema(schema: BitSchema, layouts: list[FieldLayout], total_bits: int) -> dict:
    """
    Generate JSON schema describing bit layout.

    Satisfies:
    - OUTPUT-01: Version field
    - OUTPUT-02: Per-field metadata
    - OUTPUT-03: Total bit count
    """
    return {
        "version": schema.version,  # OUTPUT-01
        "total_bits": total_bits,    # OUTPUT-03
        "fields": [                  # OUTPUT-02
            {
                "name": layout.name,
                "type": layout.type,
                "offset": layout.offset,
                "bits": layout.bits,
                "constraints": layout.constraints
            }
            for layout in layouts
        ]
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual type checking with isinstance() | Pydantic BaseModel with type hints | Pydantic v2 (2023) | Automatic validation, better errors, 10-80x faster than v1 |
| math.log2() for bit calculations | int.bit_length() | Always available | More accurate, handles edge cases (0, negatives) |
| yaml.load() | yaml.safe_load() | PyYAML 5.1 (2019) | Security - prevents code execution |
| String error messages | Structured exceptions with context | Modern Python practice | Programmatic error handling, better debugging |
| attrs for dataclasses | stdlib dataclasses | Python 3.7+ | No dependencies, built-in support |

**Deprecated/outdated:**
- Pydantic v1: Deprecated, use v2 (10-80x faster, better API)
- `yaml.load()`: Security vulnerability, use `safe_load()`
- Manual field validation: Use Pydantic validators
- `math.ceil(math.log2(n))` for bits: Use `int.bit_length()`

## Open Questions

Things that couldn't be fully resolved:

1. **Enum bit calculation for empty enum**
   - What we know: Enums with N values need `(N-1).bit_length()` bits
   - What's unclear: Should empty enums be allowed? What's the bit_length of 0?
   - Recommendation: Reject empty enums in validation (Pydantic validator)

2. **Handling integer min=max (single value)**
   - What we know: Range [5, 5] has size 0, `bit_length() = 0`
   - What's unclear: Is 0-bit field valid? How to encode/decode?
   - Recommendation: Require 1 bit minimum, or reject single-value fields as constants

3. **Field ordering guarantees**
   - What we know: Python dicts maintain insertion order (3.7+)
   - What's unclear: Should order be specified in schema format?
   - Recommendation: Document that field order in JSON/YAML is preserved (LAYOUT-02)

## Sources

### Primary (HIGH confidence)
- [Pydantic Documentation](https://docs.pydantic.dev/latest/) - v2.12.5, schema validation patterns
- [Python int.bit_length() docs](https://docs.python.org/3/library/stdtypes.html#int.bit_length) - Standard method for bit calculations
- [PyYAML Documentation](https://python.land/data-processing/python-yaml) - safe_load() security requirements
- [Python dataclasses docs](https://docs.python.org/3/library/dataclasses.html) - __post_init__, frozen, slots
- [Python JSON docs](https://docs.python.org/3/library/json.html) - Error handling, JSONDecodeError

### Secondary (MEDIUM confidence)
- [Pydantic: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/pydantic-complete-guide) - Modern patterns
- [Python YAML: How to Load, Read, and Write YAML](https://python.land/data-processing/python-yaml) - safe_load() best practices
- [jsonschema validation error handling](https://python-jsonschema.readthedocs.io/en/latest/errors/) - Fail-fast patterns
- [How to Convert Signed to Unsigned Integers in Python](https://thelinuxcode.com/how-to-convert-signed-to-unsigned-integers-in-python-fixed-width-twos-complement-and-practical-interop/) - Fixed-width calculations

### Tertiary (LOW confidence)
- WebSearch results on bit width calculations - General patterns, need verification with official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and PyPI
- Architecture: HIGH - Patterns based on Pydantic official documentation and Python best practices
- Pitfalls: HIGH - Sourced from comprehensive pitfalls research document

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (30 days - stable ecosystem, no major changes expected)
