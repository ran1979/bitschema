# BitSchema Test Suite

This directory contains comprehensive tests for the BitSchema library. Tests use pytest and Hypothesis for property-based testing.

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_integration.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=bitschema
```

## End-to-End Test Examples

Looking for examples that demonstrate the complete workflow from schema definition to encoding/decoding? Start here:

### 1. Complete Pipeline: Schema → Encode → Decode

**File:** `test_roundtrip.py`

These tests demonstrate the fundamental round-trip invariant: `decode(encode(data)) == data`

**Example test:** `test_boolean_field_roundtrip`
```python
# 1. Define bit layout
layouts = [FieldLayout(name="flag", type="boolean", offset=0, bits=1, ...)]

# 2. Encode data
original = {"flag": True}
encoded = encode(original, layouts)  # Returns: int (e.g., 1)

# 3. Decode back
decoded = decode(encoded, layouts)   # Returns: {"flag": True}

# 4. Verify round-trip
assert decoded == original
```

**Why this matters:** Uses Hypothesis to generate 500 random test cases per test, ensuring correctness across all edge cases.

**Run these tests:**
```bash
pytest tests/test_roundtrip.py -v
```

---

### 2. Schema File → Generated Code → Execution

**File:** `test_cli.py::TestCLIIntegration::test_generate_and_execute_generated_code`

This test demonstrates the complete developer workflow:

```python
# 1. Start with a schema file (JSON or YAML)
schema_file = "tests/fixtures/valid_schema.yaml"

# 2. Generate Python dataclass code
run_cli("generate", schema_file, "--output", "generated.py")

# 3. Import and use the generated code
from generated import UserFlags

# 4. Create instance and encode
user = UserFlags(active=True, age=25, status="premium")
encoded = user.encode()  # Returns: int

# 5. Decode back to object
decoded_user = UserFlags.decode(encoded)
assert decoded_user == user
```

**Run this test:**
```bash
pytest tests/test_cli.py::TestCLIIntegration::test_generate_and_execute_generated_code -v
```

---

### 3. Full Integration: File → Parse → Layout → Output

**File:** `test_integration.py::test_json_file_to_output_schema`

Demonstrates the complete programmatic API workflow:

```python
# 1. Load schema from file
from bitschema.parser import parse_schema_file
schema = parse_schema_file("tests/fixtures/valid_schema.json")

# 2. Compute bit layout
from bitschema.layout import compute_bit_layout
layouts, total_bits = compute_bit_layout(fields_dict)

# 3. Generate output schema (JSON)
from bitschema.output import generate_output_schema
output = generate_output_schema(schema.name, layouts, total_bits)

# 4. Use runtime encoding
from bitschema import encode, decode
encoded = encode({"active": True, "age": 25}, layouts)
decoded = decode(encoded, layouts)
```

**Run this test:**
```bash
pytest tests/test_integration.py::test_json_file_to_output_schema -v
```

---

### 4. CLI Commands Working Together

**File:** `test_cli.py::TestCLIIntegration::test_all_commands_work_with_json_schema`

Shows all three CLI commands working with the same schema:

```bash
# 1. Generate Python dataclass
bitschema generate schema.json > user_flags.py

# 2. Export JSON Schema (for ecosystem integration)
bitschema jsonschema schema.json > schema.jsonschema

# 3. Visualize bit layout (for documentation)
bitschema visualize schema.json
```

**Run this test:**
```bash
pytest tests/test_cli.py::TestCLIIntegration -v
```

---

## Test Categories

### Unit Tests (Fast, Focused)

- `test_layout.py` - Bit layout computation
- `test_encoder.py` - Encoding logic
- `test_decoder.py` - Decoding logic
- `test_validator.py` - Runtime validation
- `test_codegen.py` - Code generation
- `test_jsonschema.py` - JSON Schema export
- `test_visualization.py` - Layout visualization

### Property-Based Tests (Hypothesis)

- `test_roundtrip.py` - Round-trip correctness (500 examples per test)
- `test_boundary_conditions.py` - Edge cases and boundaries (500 examples per test)
- `test_codegen_equivalence.py` - Generated code matches runtime (500 examples per test)

### Integration Tests (E2E Workflows)

- `test_integration.py` - Full pipeline tests (file → parse → layout → output)
- `test_cli.py` - CLI command tests with real file I/O
- `test_date_fields.py` - Date field encoding/decoding with all resolutions
- `test_bitmask_fields.py` - Bitmask field encoding/decoding

### Fixtures

Test data files in `tests/fixtures/`:
- `valid_schema.json` - Example JSON schema
- `valid_schema.yaml` - Example YAML schema
- `invalid_schema_*.json` - Various validation error cases

## Quick Examples by Use Case

### "I want to see schema → encode → decode"

→ `test_roundtrip.py::test_multi_field_roundtrip`

### "I want to see file-based workflow"

→ `test_integration.py::test_yaml_file_to_encoding`

### "I want to see generated code in action"

→ `test_cli.py::TestCLIIntegration::test_generate_and_execute_generated_code`

### "I want to see all field types working"

→ `test_boundary_conditions.py` (covers bool, int, enum, date, bitmask, nullable)

### "I want to see error handling"

→ `test_validator.py` - Runtime validation errors
→ `test_schema_validation.py` - Schema definition errors

## Test Statistics

- **Total tests:** 356
- **Property-based tests:** 47 (with 500 examples each = 23,500+ generated test cases)
- **Test coverage:** Source + integration tests
- **Execution time:** ~3-4 seconds for full suite

## Writing New Tests

### For new field types:
1. Add unit tests in `test_encoder.py` and `test_decoder.py`
2. Add round-trip tests in `test_roundtrip.py` with Hypothesis
3. Add boundary tests in `test_boundary_conditions.py`
4. Add code generation tests in `test_codegen.py`
5. Add equivalence tests in `test_codegen_equivalence.py`

### For new features:
1. Start with integration test showing complete workflow
2. Add unit tests for individual components
3. Add property-based tests if applicable
4. Update this README with new examples

## Key Testing Patterns

### Round-trip testing:
```python
original = {"field": value}
encoded = encode(original, layouts)
decoded = decode(encoded, layouts)
assert decoded == original
```

### Property-based testing:
```python
@settings(max_examples=500)
@given(st.integers(min_value=0, max_value=255))
def test_roundtrip(self, value):
    # Test automatically runs with 500 different values
    assert decode(encode({"x": value}, layouts), layouts) == {"x": value}
```

### Equivalence testing (generated vs runtime):
```python
# Generate code
code = generate_dataclass_code(schema)
exec(code, namespace)
DataClass = namespace["MyData"]

# Compare outputs
runtime_result = encode(data, layouts)
generated_result = DataClass(**data).encode()
assert runtime_result == generated_result
```

---

**For more information:** See the main project README and `.planning/milestones/v1.0-MILESTONE-AUDIT.md`
