---
phase: 02-runtime-encoding
plan: 04
subsystem: encoding
tags: [decoder, bit-unpacking, nullable-fields, denormalization]

# Dependency graph
requires:
  - phase: 02-01
    provides: Nullable field support with presence bit tracking in FieldLayout
  - phase: 01-foundation
    provides: FieldLayout structure with offset/bits/constraints
provides:
  - Bit-unpacking decoder that transforms 64-bit integers to Python dictionaries
  - Denormalization logic for bool/int/enum types
  - Nullable field decoding with presence bit checking
affects: [02-05, round-trip-testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bit extraction pattern: (encoded >> offset) & mask"
    - "Denormalization: add min for integers, index for enums, bool() for booleans"
    - "Nullable decoding: check presence bit at offset, extract value at offset+1"

key-files:
  created:
    - bitschema/decoder.py
    - tests/test_decoder.py
  modified:
    - bitschema/__init__.py

key-decisions:
  - "decode function accepts int and layouts, returns dict"
  - "denormalize_value separates bit extraction from type conversion"
  - "Nullable fields: presence bit at offset, value bits at offset+1"

patterns-established:
  - "Mask creation: (1 << bits) - 1"
  - "Bit extraction: (encoded >> offset) & mask"
  - "Denormalization as separate function for testability"

# Metrics
duration: 2.5min
completed: 2026-02-19
---

# Phase 02 Plan 04: Bit-Unpacking Decoder Summary

**Decoder module transforms 64-bit integers to Python dicts using bitwise extraction and denormalization with nullable support**

## Performance

- **Duration:** 2.5 min
- **Started:** 2026-02-19T12:29:08Z
- **Completed:** 2026-02-19T12:31:39Z
- **Tasks:** 1 TDD task (2 commits: test, feat)
- **Files created:** 2
- **Files modified:** 1

## Accomplishments

- Implemented decode function for 64-bit integer to dict transformation
- Created denormalize_value helper for type conversion (bool/int/enum)
- Added nullable field support with presence bit checking
- Comprehensive test coverage: 18 tests for all field types and combinations
- Exported decode and denormalize_value from bitschema package

## Task Commits

Each task was committed atomically following TDD cycle:

1. **Task 1: Bit-unpacking decoder** (TDD)
   - `83b0c90` (test: add failing tests for bit-unpacking decoder)
   - `4b93ab5` (feat: implement bit-unpacking decoder with nullable support)

_Note: No refactor phase needed - implementation was clean on first pass_

## Files Created/Modified

**Created:**
- `bitschema/decoder.py` - Decoder module with decode and denormalize_value functions
- `tests/test_decoder.py` - 18 tests covering all decoder scenarios

**Modified:**
- `bitschema/__init__.py` - Added decode and denormalize_value exports

## Decisions Made

**1. Separate denormalize_value function**
- Extracted denormalization logic into standalone function
- Improves testability and reusability
- Clear separation: decode handles bit extraction, denormalize_value handles type conversion

**2. Bit extraction pattern**
- Mask creation: `(1 << bits) - 1`
- Extraction: `(encoded >> offset) & mask`
- Matches research pattern, mathematically correct

**3. Nullable field decoding**
- Check presence bit at layout.offset
- If presence = 0: return None
- If presence = 1: extract value from offset+1 with (bits-1) width
- Consistent with layout.py presence bit design

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TDD cycle worked smoothly, all 18 tests passed on first implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Decoder complete and ready for round-trip testing
- All field types supported: boolean, integer, enum
- Nullable fields handled correctly with presence bits
- Test coverage comprehensive (18 tests, all passing)

**Ready for:** 02-05 (Round-trip encoding/decoding tests)

---
*Phase: 02-runtime-encoding*
*Completed: 2026-02-19*
