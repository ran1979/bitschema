# BitSchema

## What This Is

BitSchema is a Python library that automatically derives optimal bit-level layouts for structured data and packs them into single 64-bit integers. Users define fields via JSON/YAML config (dates, enums, booleans, bounded integers), and BitSchema generates both a JSON schema describing the bit layout and Python dataclass encoders/decoders that safely pack and unpack data with zero tolerance for overflow.

## Core Value

Data packing must be mathematically correct and deterministic - no silent truncation, no overflow, no guessing. Every field gets exactly the bits it needs, no more, no less.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Accept JSON/YAML field definitions with type constraints (boolean, bounded integer, enum, date with resolution)
- [ ] Compute minimum required bits per field with explicit overflow detection
- [ ] Generate deterministic bit layouts with field offsets and widths
- [ ] Output versioned JSON schema describing the complete bit structure
- [ ] Generate Python dataclass with encode() and decode() methods from schema
- [ ] Support runtime encoding/decoding using schema without code generation
- [ ] Implement nullable fields using presence bits (1 extra bit per nullable field)
- [ ] Validate all values during encoding and fail fast on overflow/out-of-range
- [ ] Ensure symmetric round-trip correctness (encode → decode returns original values)
- [ ] Pack all fields into single 64-bit integer with total bit count validation

### Out of Scope

- Multi-integer support (>64 bits) — v1 limited to single integer
- Schema evolution and migration — foundation can be laid (version field) but full migration is post-v1
- Nested structs or complex types — only flat field lists in v1
- Arbitrary byte buffers — integers only
- Runtime performance optimization — correctness first, speed later
- Language bindings beyond Python — TypeScript/other languages are future work

## Context

**Use Cases:**
- User segmentation: Store which categories/segments apply to a user profile (bit flags)
- IoT sensor data: Pack timestamp + sensor readings + status codes compactly
- Metadata compression: Store dates with associated type/status fields in databases or network protocols

**Technical Environment:**
- Python 3.10+ as primary implementation language
- JSON/YAML for schema input and output
- Focus on developer experience: clear error messages, mathematical correctness, comprehensive tests

**Quality Requirements:**
- Explicit bit allocation calculations with justification
- No magic numbers or dynamic guessing
- Clear overflow/boundary handling
- Round-trip tests for every supported type
- Generated code must be readable and debuggable

## Constraints

- **Storage**: Single 64-bit integer maximum — total field bits cannot exceed 64
- **Error Handling**: Fail-fast validation — never allow silent truncation or overflow
- **Language**: Python 3.10+ — leveraging modern type hints and dataclasses
- **Input Format**: JSON or YAML configuration files — no Python API for field definition in v1
- **Determinism**: Bit layouts must be reproducible — same input always produces same schema

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 64-bit integer limit for v1 | Simplifies implementation, covers most common use cases (flags, metadata), validates the core concept before expanding | — Pending |
| Fail-fast validation | Prevents data corruption, makes bugs obvious immediately rather than silently corrupting data | — Pending |
| JSON/YAML input over Python API | Forces schema to be portable and language-agnostic, enables future multi-language support | — Pending |
| Generated dataclass output | Provides type-safe, IDE-friendly encoding/decoding with zero runtime schema parsing overhead | — Pending |
| Presence bits for nullables | Explicit and unambiguous, doesn't rely on magic values that could conflict with valid data | — Pending |

---
*Last updated: 2026-02-19 after initialization*
