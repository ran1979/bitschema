# Roadmap: BitSchema

## Overview

BitSchema delivers mathematically correct, deterministic bit-packing for Python through four focused phases: establishing core schema processing and bit manipulation primitives, building runtime encoding with fail-fast validation, generating static Python code for developer experience, and completing the system with comprehensive testing and advanced field types. Each phase delivers verifiable capabilities that build toward a production-ready library where data packing is never silent, never wrong, and always reproducible.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Schema processing and bit manipulation primitives
- [x] **Phase 2: Runtime Encoding** - Full encode/decode with validation
- [x] **Phase 3: Code Generation** - Static code generation and output formats
- [ ] **Phase 4: Testing & Advanced Types** - Comprehensive testing and advanced field types

## Phase Details

### Phase 1: Foundation
**Goal**: Developers can define schemas and BitSchema computes correct bit layouts
**Depends on**: Nothing (first phase)
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04, SCHEMA-05, TYPE-01, TYPE-02, TYPE-03, TYPE-04, TYPE-05, LAYOUT-01, LAYOUT-02, LAYOUT-03, LAYOUT-04, LAYOUT-05, OUTPUT-01, OUTPUT-02, OUTPUT-03
**Success Criteria** (what must be TRUE):
  1. Developer can write JSON or YAML file defining fields with types and constraints
  2. System validates schema format and fails fast with clear errors on invalid schemas
  3. System computes deterministic bit offsets for all fields in declared order
  4. System outputs JSON schema describing complete bit layout with offsets and widths
  5. System rejects schemas exceeding 64-bit limit with explanation of which fields cause overflow
**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — Project setup with Pydantic, PyYAML, pytest
- [x] 01-02-PLAN.md — Schema models TDD (Pydantic validation)
- [x] 01-03-PLAN.md — Bit layout computation TDD (offset calculation)
- [x] 01-04-PLAN.md — Schema file parser TDD (JSON/YAML loading)
- [x] 01-05-PLAN.md — Schema output and integration TDD (JSON generation)

### Phase 2: Runtime Encoding
**Goal**: Developers can encode and decode data at runtime using compiled schemas
**Depends on**: Phase 1
**Requirements**: ENCODE-01, ENCODE-02, ENCODE-03, ENCODE-04, ENCODE-05, ENCODE-06, DECODE-01, DECODE-02, DECODE-03, DECODE-04, DECODE-05, TYPE-06
**Success Criteria** (what must be TRUE):
  1. Developer can load compiled schema and encode Python dict to 64-bit integer
  2. System validates all field values against constraints before encoding and fails with clear error on violation
  3. Developer can decode 64-bit integer back to Python dict using same schema
  4. Round-trip correctness verified for all field types (encode then decode returns original values)
  5. Nullable fields work correctly with None values encoded using presence bits
**Plans**: 5 plans

Plans:
- [x] 02-01-PLAN.md — Nullable field support in schema models (TDD)
- [x] 02-02-PLAN.md — Runtime validation module with EncodingError (TDD)
- [x] 02-03-PLAN.md — Bit-packing encoder with LSB-first accumulator (TDD)
- [x] 02-04-PLAN.md — Bit-unpacking decoder with extraction logic (TDD)
- [x] 02-05-PLAN.md — Round-trip tests with Hypothesis property-based testing (TDD)

### Phase 3: Code Generation
**Goal**: Developers can generate static Python dataclasses with type-safe encode/decode methods
**Depends on**: Phase 2
**Requirements**: CODEGEN-01, CODEGEN-02, CODEGEN-03, CODEGEN-04, CODEGEN-05, CODEGEN-06, OUTPUT-04, OUTPUT-05
**Success Criteria** (what must be TRUE):
  1. Developer can run CLI command to generate Python dataclass from schema
  2. Generated code includes full type hints and works with IDE autocomplete
  3. Generated encode/decode methods produce identical results to runtime encoding
  4. Generated code is readable with clear formatting and helpful docstrings
  5. Bit layout visualization shows exact bit positions for all fields in human-readable format
**Plans**: 4 plans

Plans:
- [x] 03-01-PLAN.md — Dataclass code generation with encode/decode methods (TDD)
- [x] 03-02-PLAN.md — JSON Schema Draft 2020-12 export (TDD)
- [x] 03-03-PLAN.md — Bit layout visualization tables (TDD)
- [x] 03-04-PLAN.md — CLI wrapper with argparse subcommands (gap closure)

### Phase 4: Testing & Advanced Types
**Goal**: Library has comprehensive test coverage and supports advanced field types
**Depends on**: Phase 3
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TYPE-07, TYPE-08, TYPE-09
**Success Criteria** (what must be TRUE):
  1. Test suite includes round-trip tests for all field types with boundary conditions
  2. Property-based tests discover edge cases in bit-packing logic automatically
  3. Developer can use date fields with configurable resolution and range constraints
  4. Developer can use bitmask fields for multiple boolean flags
  5. Generated code and runtime encoding produce identical results for all test cases
**Plans**: 4 plans

Plans:
- [ ] 04-01-PLAN.md — Comprehensive test suite with Hypothesis (boundary conditions, nullable combinations)
- [ ] 04-02-PLAN.md — Date field support TDD (day/hour/minute/second resolution with range constraints)
- [ ] 04-03-PLAN.md — Bitmask field support TDD (multiple boolean flags with position validation)
- [ ] 04-04-PLAN.md — Code generation for advanced types and equivalence testing

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|-----------|-----------|
| 1. Foundation | 5/5 | Complete ✓ | 2026-02-19 |
| 2. Runtime Encoding | 5/5 | Complete ✓ | 2026-02-19 |
| 3. Code Generation | 4/4 | Complete ✓ | 2026-02-19 |
| 4. Testing & Advanced Types | 0/4 | Not started | - |
