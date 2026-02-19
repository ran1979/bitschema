---
phase: 03-code-generation
plan: 01
subsystem: codegen
tags: [python, dataclass, code-generation, ast, ruff]

# Dependency graph
requires:
  - phase: 02-runtime-encoding
    provides: encoder.py and decoder.py with normalize/denormalize logic
provides:
  - Dataclass code generator producing type-safe Python with encode/decode methods
  - AST-based syntax validation
  - Optional Ruff formatting with graceful fallback
  - Helper functions for normalize/denormalize expression generation
affects: [03-02-json-schema, 03-03-visualization, 04-cli]

# Tech tracking
tech-stack:
  added: [ast (stdlib), subprocess (for Ruff)]
  patterns: [f-string code generation with textwrap, LSB-first accumulator in generated code, bit extraction in generated code]

key-files:
  created:
    - bitschema/codegen.py
    - tests/test_codegen.py
  modified:
    - bitschema/__init__.py

key-decisions:
  - "Use f-strings with textwrap for code generation (readable, maintainable)"
  - "Validate with ast.parse before returning (fail-fast on invalid syntax)"
  - "Optional Ruff formatting with graceful fallback (better UX than hard dependency)"
  - "Extract helper functions for normalize/denormalize (DRY, single source of truth)"
  - "Generated code mirrors runtime encoder/decoder exactly (verified by round-trip tests)"

patterns-established:
  - "Code generation pattern: helper functions → method assembly → full class generation → validation"
  - "TDD with round-trip correctness tests: ensure generated code matches runtime behavior"

# Metrics
duration: 4min
completed: 2026-02-19
---

# Phase 03 Plan 01: Dataclass Code Generator Summary

**Type-safe dataclass generator with encode/decode methods matching runtime encoder/decoder, validated via ast.parse and round-trip tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-19T14:02:13Z
- **Completed:** 2026-02-19T14:06:31Z
- **Tasks:** 1 TDD task (RED → GREEN → REFACTOR)
- **Files modified:** 3

## Accomplishments
- Complete dataclass code generation from BitSchema schemas (394 lines)
- Generated code produces identical results to runtime encoder/decoder (verified by tests)
- All field types supported (bool, int, enum, nullable)
- Comprehensive test suite with 28 tests covering all edge cases
- Refactored to eliminate code duplication via helper functions

## Task Commits

TDD workflow with three commits:

1. **RED: Failing tests** - `35aecfc` (test)
   - 28 comprehensive tests for code generation
   - Type hints, field definitions, encode/decode methods
   - Round-trip correctness tests
   - Syntax validation tests

2. **GREEN: Implementation** - `36a1f93` (feat)
   - bitschema/codegen.py with 7 functions
   - generate_field_type_hint, generate_field_definitions
   - generate_encode_method, generate_decode_method
   - generate_dataclass_code, format_generated_code, validate_generated_code
   - Updated bitschema/__init__.py to export generate_dataclass_code
   - All 28 tests passing

3. **REFACTOR: Extract helpers** - `8adc85d` (refactor)
   - Extracted _generate_normalize_expression() helper
   - Extracted _generate_denormalize_statements() helper
   - Reduced duplication, improved maintainability
   - All 28 tests still passing

## Files Created/Modified

- `bitschema/codegen.py` - Dataclass code generator with 7 functions (394 lines)
  - Maps field definitions to Python type hints (int | None for nullable)
  - Generates LSB-first accumulator pattern (mirrors encoder.py)
  - Generates bit extraction pattern (mirrors decoder.py)
  - Validates syntax with ast.parse, formats with optional Ruff

- `tests/test_codegen.py` - Comprehensive test suite (533 lines, 28 tests)
  - Type hint generation tests (6 tests)
  - Field definition tests (4 tests)
  - Encode method generation tests (4 tests)
  - Decode method generation tests (3 tests)
  - Complete dataclass generation tests (4 tests)
  - Round-trip correctness tests (4 tests)
  - Code formatting tests (3 tests)

- `bitschema/__init__.py` - Added generate_dataclass_code export

## Decisions Made

1. **f-strings with textwrap for code generation**
   - Rationale: Readable and maintainable, no template engine dependency
   - Outcome: Clean code generation logic

2. **ast.parse validation before returning**
   - Rationale: Fail-fast on syntax errors, catch bugs immediately
   - Outcome: Generated code always syntactically valid

3. **Optional Ruff formatting with graceful fallback**
   - Rationale: Better UX than hard dependency, works even if Ruff unavailable
   - Outcome: Formatted code when possible, unformatted when not

4. **Extract normalize/denormalize helper functions**
   - Rationale: DRY principle, eliminate duplication between nullable/non-nullable paths
   - Outcome: Single source of truth, easier to maintain

5. **Generated code must match runtime encoder/decoder**
   - Rationale: Zero-tolerance for behavioral differences
   - Outcome: Round-trip tests verify identical results

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test cases for signed integers**
- **Found during:** GREEN phase test execution
- **Issue:** Test cases used negative min values without setting signed=True flag
- **Fix:** Added signed=True to IntFieldDefinition in two test cases
- **Files modified:** tests/test_codegen.py
- **Verification:** All 28 tests pass
- **Committed in:** 36a1f93 (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (test setup bug)
**Impact on plan:** Minor test fix, no impact on implementation scope

## Issues Encountered

None - TDD workflow proceeded smoothly with expected RED → GREEN → REFACTOR cycle.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Code generation complete and fully tested
- Ready for JSON Schema export (03-02) which can reference generated code
- Ready for visualization (03-03) which may want to show generated code
- CLI tools (phase 04) can use generate_dataclass_code() to create Python files

**Blockers:** None

**Concerns:** None - implementation matches plan exactly

---
*Phase: 03-code-generation*
*Completed: 2026-02-19*
