---
phase: 03-code-generation
plan: 04
subsystem: cli
tags: [argparse, cli, command-line, console-scripts]

# Dependency graph
requires:
  - phase: 03-code-generation/03-01
    provides: generate_dataclass_code function for Python code generation
  - phase: 03-code-generation/03-02
    provides: generate_json_schema function for JSON Schema export
  - phase: 03-code-generation/03-03
    provides: visualize_bit_layout functions for ASCII/markdown tables
provides:
  - CLI entry point accessible as 'bitschema' command after installation
  - Three subcommands: generate, jsonschema, visualize
  - Argparse-based argument parsing with help messages
  - Console script registration via pyproject.toml [project.scripts]
  - Comprehensive CLI integration tests using subprocess
affects: [user-documentation, deployment, package-distribution]

# Tech tracking
tech-stack:
  added: []
  patterns: [argparse-subcommands, helper-function-for-schema-conversion, subprocess-testing]

key-files:
  created: [bitschema/__main__.py, tests/test_cli.py]
  modified: [pyproject.toml]

key-decisions:
  - "argparse over click/typer: Zero new dependencies, standard Python CLI pattern"
  - "Helper function _schema_fields_to_list: Converts schema.fields dict to list format for compute_bit_layout"
  - "Subprocess testing pattern: Tests actual CLI invocation as users would experience it"
  - "Error handling with sys.exit(1): Standard CLI error pattern with clear error messages to stderr"

patterns-established:
  - "CLI subcommand structure: main() → subparsers → cmd_* functions → set_defaults(func=cmd_*)"
  - "Output mode pattern: --output for file, stdout if omitted, status to stderr"
  - "Schema conversion helper: Reusable pattern for converting Pydantic models to dict lists"

# Metrics
duration: 3.5min
completed: 2026-02-19
---

# Phase 3 Plan 4: CLI Wrapper Summary

**Argparse-based CLI with generate/jsonschema/visualize subcommands, console script registration, and 24 comprehensive integration tests**

## Performance

- **Duration:** 3.5 min
- **Started:** 2026-02-19T14:28:40Z
- **Completed:** 2026-02-19T14:32:10Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- CLI entry point with three subcommands accessible via `bitschema` command
- Support for both stdout and file output modes across all subcommands
- Comprehensive error handling with clear messages for missing files and invalid schemas
- 24 integration tests covering all subcommands, error cases, and output modes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CLI entry point with argparse subcommands** - `4a9a6cf` (feat)
2. **Task 2: Add console_scripts entry point to pyproject.toml** - `4ac4a62` (feat)
3. **Task 3: Create CLI integration tests** - `ed1cea4` (test)

## Files Created/Modified
- `bitschema/__main__.py` - CLI entry point with argparse, three subcommands, schema conversion helper
- `pyproject.toml` - Added [project.scripts] section for console script registration
- `tests/test_cli.py` - 24 comprehensive integration tests using subprocess

## Decisions Made

**argparse over click/typer:** Chose stdlib argparse to avoid adding new dependencies. Project currently has only pydantic, PyYAML, and tabulate - keeping dependency footprint minimal is important for a library focused on mathematical correctness.

**Helper function for schema conversion:** Created `_schema_fields_to_list()` to convert schema.fields dict (Pydantic models) into list format expected by `compute_bit_layout()`. This pattern could be reused elsewhere if needed.

**Subprocess testing approach:** Tests invoke actual CLI via subprocess rather than calling main() directly. This verifies the full user experience including argument parsing, error handling, and output formatting.

**Error messages to stderr, results to stdout:** Followed Unix convention - status/diagnostic messages to stderr, actual output to stdout. Enables `bitschema generate schema.yaml > output.py` to work cleanly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertions to match actual help descriptions**
- **Found during:** Task 3 (running CLI integration tests)
- **Issue:** Test assertions expected short help text from argparse 'help' parameter, but actual output showed longer 'description' text
- **Fix:** Updated test assertions to match actual help descriptions
- **Files modified:** tests/test_cli.py
- **Verification:** All 24 tests pass
- **Committed in:** ed1cea4 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fix to match actual CLI behavior. No functional changes to implementation.

## Issues Encountered

**Schema conversion challenge:** Initial implementation passed `schema` object directly to `compute_bit_layout()`, but that function expects a list of field dicts. Created helper function `_schema_fields_to_list()` to handle the conversion by extracting fields and converting Pydantic models to dicts.

**Solution:** Helper function iterates through `schema.fields.items()`, detects field type via `isinstance()`, and builds appropriate dict structure. This pattern mirrors the approach used in `tests/test_roundtrip.py`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Phase 3 Code Generation is now COMPLETE:**
- ✓ Dataclass code generation (03-01)
- ✓ JSON Schema export (03-02)
- ✓ Bit layout visualization (03-03)
- ✓ CLI wrapper (03-04)

**Ready for Phase 4:** All code generation capabilities are accessible via CLI, programmatic API, and thoroughly tested. Users can now:
1. `bitschema generate schema.yaml --output person.py` → Generate type-safe dataclass
2. `bitschema jsonschema schema.yaml` → Export JSON Schema for interoperability
3. `bitschema visualize schema.yaml --format markdown` → View bit layout

No blockers for final phase.

---
*Phase: 03-code-generation*
*Completed: 2026-02-19*
