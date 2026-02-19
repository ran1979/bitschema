# BitSchema

## What This Is

BitSchema is a Python library that automatically derives optimal bit-level layouts for structured data and packs them into single 64-bit integers. Users define fields via JSON/YAML config (dates, enums, booleans, bounded integers), and BitSchema generates both a JSON schema describing the bit layout and Python dataclass encoders/decoders that safely pack and unpack data with zero tolerance for overflow.

## Core Value

Data packing must be mathematically correct and deterministic - no silent truncation, no overflow, no guessing. Every field gets exactly the bits it needs, no more, no less.

## Requirements

### Validated

- ✓ Accept JSON/YAML field definitions with type constraints (boolean, bounded integer, enum, date with resolution, bitmask) — Shipped: v1.0
- ✓ Compute minimum required bits per field with explicit overflow detection — Shipped: v1.0
- ✓ Generate deterministic bit layouts with field offsets and widths — Shipped: v1.0
- ✓ Output versioned JSON schema describing the complete bit structure — Shipped: v1.0
- ✓ Generate Python dataclass with encode() and decode() methods from schema — Shipped: v1.0
- ✓ Support runtime encoding/decoding using schema without code generation — Shipped: v1.0
- ✓ Implement nullable fields using presence bits (1 extra bit per nullable field) — Shipped: v1.0
- ✓ Validate all values during encoding and fail fast on overflow/out-of-range — Shipped: v1.0
- ✓ Ensure symmetric round-trip correctness (encode → decode returns original values) — Shipped: v1.0
- ✓ Pack all fields into single 64-bit integer with total bit count validation — Shipped: v1.0
- ✓ Export JSON Schema Draft 2020-12 format for ecosystem integration — Shipped: v1.0
- ✓ Generate bit layout visualization in markdown format — Shipped: v1.0
- ✓ CLI tool with generate/jsonschema/visualize commands — Shipped: v1.0
- ✓ Date fields with configurable resolution (day/hour/minute/second) — Shipped: v1.0
- ✓ Bitmask fields for multiple boolean flags — Shipped: v1.0
- ✓ Comprehensive test suite with property-based testing — Shipped: v1.0

### Active

(None — next milestone will define new requirements)

### Out of Scope

- Multi-integer support (>64 bits) — v1 limited to single integer
- Schema evolution and migration — deferred to v2
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
| 64-bit integer limit for v1 | Simplifies implementation, covers most common use cases (flags, metadata), validates the core concept before expanding | ✓ Shipped: v1.0 — Comprehensive 64-bit implementation with validation |
| Fail-fast validation | Prevents data corruption, makes bugs obvious immediately rather than silently corrupting data | ✓ Shipped: v1.0 — EncodingError with clear messages |
| JSON/YAML input over Python API | Forces schema to be portable and language-agnostic, enables future multi-language support | ✓ Shipped: v1.0 — Dual parser with Pydantic validation |
| Generated dataclass output | Provides type-safe, IDE-friendly encoding/decoding with zero runtime schema parsing overhead | ✓ Shipped: v1.0 — Full type hints, docstrings, IDE support |
| Presence bits for nullables | Explicit and unambiguous, doesn't rely on magic values that could conflict with valid data | ✓ Shipped: v1.0 — Nullable support across all field types |
| TDD methodology | Ensures correctness from first commit, catches regressions immediately | ✓ Shipped: v1.0 — 356 tests, 47 property-based |
| LSB-first accumulator pattern | Platform-independent, mathematically clear, easy to debug | ✓ Shipped: v1.0 — Used in encoder/decoder/codegen |
| Offset-from-epoch date encoding | Compact representation, configurable resolution, deterministic | ✓ Shipped: v1.0 — 4 resolutions (day/hour/minute/second) |
| Code generation equivalence | Generated code must match runtime exactly — zero divergence | ✓ Shipped: v1.0 — 7 equivalence tests, 3,500+ examples verified |

## Milestones

### v1.0 MVP (Shipped: 2026-02-19)

**What we built:**
Production-ready Python library for mathematically correct, deterministic bit-packing into 64-bit integers.

**Key accomplishments:**
- Schema definition and validation with JSON/YAML support, fail-fast error handling, and 64-bit limit enforcement
- Runtime encoding/decoding with LSB-first accumulator pattern, presence bits for nullable fields, and comprehensive round-trip testing
- Static code generation producing type-safe Python dataclasses with encode/decode methods matching runtime exactly
- CLI tool with three commands (generate, jsonschema, visualize) for complete developer workflow
- Advanced field types: date fields with 4 resolution levels (day/hour/minute/second) and bitmask fields for compact flag storage
- Comprehensive test suite with 356 tests including 47 property-based tests generating 5,000+ test cases via Hypothesis

**Stats:**
- 85 files created/modified
- 10,042 lines of Python (source + tests)
- 4 phases, 18 plans, ~60 tasks
- 5 hours from start to ship (same-day development)

**Archive:** `.planning/milestones/v1.0-*`

---
*Last updated: 2026-02-19 after v1.0 completion*
