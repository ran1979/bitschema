# Requirements: BitSchema

**Defined:** 2026-02-19
**Core Value:** Data packing must be mathematically correct and deterministic - no silent truncation, no overflow, no guessing

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Schema Definition

- [ ] **SCHEMA-01**: System accepts JSON file with field definitions (name, type, constraints)
- [ ] **SCHEMA-02**: System accepts YAML file with field definitions
- [ ] **SCHEMA-03**: System validates schema format against specification
- [ ] **SCHEMA-04**: System validates field names are unique within schema
- [ ] **SCHEMA-05**: System validates total bits do not exceed 64-bit limit

### Field Types - Core

- [ ] **TYPE-01**: System supports boolean fields (1 bit)
- [ ] **TYPE-02**: System supports bounded integer fields with min/max constraints
- [ ] **TYPE-03**: System supports enum fields with value list (index-based encoding)
- [ ] **TYPE-04**: System computes minimum required bits for each field type
- [ ] **TYPE-05**: System validates integer min/max values fit within computed bits

### Field Types - Advanced

- [ ] **TYPE-06**: System supports nullable fields with presence bit (adds 1 bit)
- [ ] **TYPE-07**: System supports date fields with configurable resolution (day, hour, minute, second)
- [ ] **TYPE-08**: System supports date range constraints (min date, max date)
- [ ] **TYPE-09**: System supports bitmask fields (multiple boolean flags)

### Bit Layout Calculation

- [ ] **LAYOUT-01**: System computes deterministic bit offsets for all fields
- [ ] **LAYOUT-02**: System assigns fields in declared order (stable ordering)
- [ ] **LAYOUT-03**: System validates no bit offset overlaps
- [ ] **LAYOUT-04**: System calculates total bit count across all fields
- [ ] **LAYOUT-05**: System rejects schemas exceeding 64-bit total

### Schema Output

- [ ] **OUTPUT-01**: System generates JSON schema with version field
- [ ] **OUTPUT-02**: JSON schema includes per-field: name, type, offset, bits, constraints
- [ ] **OUTPUT-03**: JSON schema includes total bit count
- [ ] **OUTPUT-04**: System exports JSON Schema format (ecosystem integration)
- [ ] **OUTPUT-05**: System generates bit layout visualization (ASCII or markdown table)

### Runtime Encoding

- [ ] **ENCODE-01**: System encodes Python dict to 64-bit integer using schema
- [ ] **ENCODE-02**: System validates all required fields are present
- [ ] **ENCODE-03**: System validates values are within field constraints before encoding
- [ ] **ENCODE-04**: System fails fast with clear error on constraint violation (field name, value, limit)
- [ ] **ENCODE-05**: System handles endianness consistently (platform-independent)
- [ ] **ENCODE-06**: System encodes nullable fields using presence bit

### Runtime Decoding

- [ ] **DECODE-01**: System decodes 64-bit integer to Python dict using schema
- [ ] **DECODE-02**: System extracts fields using bit masks at computed offsets
- [ ] **DECODE-03**: System converts raw bit values back to semantic values (dates, enums, booleans)
- [ ] **DECODE-04**: System decodes nullable fields correctly (None when presence bit is 0)
- [ ] **DECODE-05**: System ensures round-trip correctness (encode(decode(x)) == x)

### Code Generation

- [ ] **CODEGEN-01**: System generates Python dataclass from schema
- [ ] **CODEGEN-02**: Generated dataclass has encode() method returning int
- [ ] **CODEGEN-03**: Generated dataclass has decode() class method accepting int
- [ ] **CODEGEN-04**: Generated code includes full type hints
- [ ] **CODEGEN-05**: Generated code is formatted and readable
- [ ] **CODEGEN-06**: Generated code includes docstrings with field descriptions

### Testing & Validation

- [ ] **TEST-01**: System includes test suite with round-trip tests for all field types
- [ ] **TEST-02**: System tests boundary conditions (min, max, overflow)
- [ ] **TEST-03**: System tests nullable field combinations
- [ ] **TEST-04**: System validates generated code produces same results as runtime encoder
- [ ] **TEST-05**: System includes property-based tests for edge case discovery

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Schema Evolution

- **EVOLVE-01**: System supports schema versioning with migration paths
- **EVOLVE-02**: System validates backward compatibility between schema versions
- **EVOLVE-03**: System supports field addition without breaking old data

### Advanced Types

- **ADVANCED-01**: System supports nested struct fields
- **ADVANCED-02**: System supports array/list fields with length constraints
- **ADVANCED-03**: System supports variable-length encoding (varints)

### Performance

- **PERF-01**: System includes C/Rust extension for performance-critical paths
- **PERF-02**: System supports batch encoding/decoding operations
- **PERF-03**: System caches compiled schemas for reuse

### Multi-Language

- **LANG-01**: System generates TypeScript encoder/decoder from schema
- **LANG-02**: System generates Rust encoder/decoder from schema
- **LANG-03**: System ensures cross-language compatibility

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-integer support (>64 bits) | V1 focuses on single integer to validate core concept; expanding to byte buffers adds complexity |
| Python API for schema definition | Config files keep schema portable and language-agnostic; Python DSL can be added later |
| Automatic schema inference from data | Requires dynamic analysis; v1 is explicit definition only |
| Compression algorithms | Bit-packing is structural, not compression; avoid scope creep into gzip territory |
| Encryption or security features | Serialization only; security is orthogonal concern |
| Network protocol implementation | BitSchema is encoding library; protocol layers (framing, headers) are separate |
| Reflection-based runtime | Generated code and schema-based runtime cover use cases; reflection adds complexity |
| Backward compatibility for v1 schemas | V1 is MVP; schema evolution deferred to v2 with proper versioning design |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCHEMA-01 | Phase 1 | Pending |
| SCHEMA-02 | Phase 1 | Pending |
| SCHEMA-03 | Phase 1 | Pending |
| SCHEMA-04 | Phase 1 | Pending |
| SCHEMA-05 | Phase 1 | Pending |
| TYPE-01 | Phase 1 | Pending |
| TYPE-02 | Phase 1 | Pending |
| TYPE-03 | Phase 1 | Pending |
| TYPE-04 | Phase 1 | Pending |
| TYPE-05 | Phase 1 | Pending |
| TYPE-06 | Phase 2 | Pending |
| TYPE-07 | Phase 4 | Pending |
| TYPE-08 | Phase 4 | Pending |
| TYPE-09 | Phase 4 | Pending |
| LAYOUT-01 | Phase 1 | Pending |
| LAYOUT-02 | Phase 1 | Pending |
| LAYOUT-03 | Phase 1 | Pending |
| LAYOUT-04 | Phase 1 | Pending |
| LAYOUT-05 | Phase 1 | Pending |
| OUTPUT-01 | Phase 1 | Pending |
| OUTPUT-02 | Phase 1 | Pending |
| OUTPUT-03 | Phase 1 | Pending |
| OUTPUT-04 | Phase 3 | Pending |
| OUTPUT-05 | Phase 3 | Pending |
| ENCODE-01 | Phase 2 | Pending |
| ENCODE-02 | Phase 2 | Pending |
| ENCODE-03 | Phase 2 | Pending |
| ENCODE-04 | Phase 2 | Pending |
| ENCODE-05 | Phase 2 | Pending |
| ENCODE-06 | Phase 2 | Pending |
| DECODE-01 | Phase 2 | Pending |
| DECODE-02 | Phase 2 | Pending |
| DECODE-03 | Phase 2 | Pending |
| DECODE-04 | Phase 2 | Pending |
| DECODE-05 | Phase 2 | Pending |
| CODEGEN-01 | Phase 3 | Pending |
| CODEGEN-02 | Phase 3 | Pending |
| CODEGEN-03 | Phase 3 | Pending |
| CODEGEN-04 | Phase 3 | Pending |
| CODEGEN-05 | Phase 3 | Pending |
| CODEGEN-06 | Phase 3 | Pending |
| TEST-01 | Phase 4 | Pending |
| TEST-02 | Phase 4 | Pending |
| TEST-03 | Phase 4 | Pending |
| TEST-04 | Phase 4 | Pending |
| TEST-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 46 total
- Mapped to phases: 46 (100% coverage)
- Unmapped: 0

---
*Requirements defined: 2026-02-19*
*Last updated: 2026-02-19 after roadmap creation*
