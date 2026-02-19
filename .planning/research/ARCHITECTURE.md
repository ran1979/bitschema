# Architecture Research: Schema-Driven Bit-Packing Systems

**Domain:** Schema-driven serialization and bit-packing systems
**Researched:** 2026-02-19
**Confidence:** HIGH

## Standard Architecture

Schema-driven bit-packing systems follow a consistent three-stage pipeline architecture observed across Protocol Buffers, FlatBuffers, Cap'n Proto, and similar serialization systems. The architecture separates schema processing (compile-time) from encoding/decoding (runtime).

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPILE-TIME LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Schema  │→ │  Schema  │→ │   Bit    │→ │   Code   │    │
│  │  Parser  │  │Validator │  │Allocator │  │Generator │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│       ↓             ↓             ↓             ↓           │
│   Parse AST   →  Validate   →  Layout    → Templates       │
├─────────────────────────────────────────────────────────────┤
│                     ARTIFACT LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Intermediate Schema (JSON/Binary)           │    │
│  │  - Field definitions with bit offsets               │    │
│  │  - Computed layout (size, alignment)                │    │
│  │  - Type metadata                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Generated Code (Python/C++/etc)             │    │
│  │  - Dataclasses/structs with encode/decode methods   │    │
│  │  - Type-safe accessors                              │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                      RUNTIME LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Schema   │  │  Bit     │  │  Field   │  │ Encoder/ │    │
│  │ Loader   │  │ Packer   │  │Validator │  │ Decoder  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│       ↓             ↓             ↓             ↓           │
│   Load JSON  →  Pack bits  →  Validate   →  Bytes          │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Schema Parser** | Parse schema definition files (JSON/YAML/.proto) into AST | Recursive descent parser or JSON/YAML library |
| **Schema Validator** | Verify field types, detect conflicts, check constraints | Visitor pattern over AST, type checker |
| **Bit Allocator** | Calculate bit offsets, handle alignment, compute total size | Greedy allocation algorithm with alignment rules |
| **Code Generator** | Generate language-specific code from schema | Template-based or AST-based code generation |
| **Schema Loader** | Load compiled schema at runtime for dynamic encoding | JSON parser with caching |
| **Bit Packer** | Pack/unpack field values to/from bit positions | Bitwise operations with struct module or similar |
| **Field Validator** | Runtime validation of field values against schema | Type checking, range validation |
| **Encoder/Decoder** | Serialize objects to bytes / deserialize bytes to objects | Orchestrates packer + validator |

## Recommended Project Structure

Based on analysis of Protocol Buffers, FlatBuffers, and Python serialization libraries (bitstring, bitstruct, construct), the recommended structure separates compile-time tooling from runtime libraries.

```
BitSchema/
├── bitschema/              # Runtime library (installed via pip)
│   ├── __init__.py
│   ├── schema.py           # Schema loading and representation
│   ├── packer.py           # Bit-packing operations
│   ├── encoder.py          # High-level encode/decode API
│   ├── validator.py        # Runtime field validation
│   └── types.py            # Type system definitions
├── bitschema_compiler/     # Compile-time code generation tool
│   ├── __init__.py
│   ├── parser.py           # Parse JSON/YAML schema files
│   ├── validator.py        # Schema validation logic
│   ├── allocator.py        # Bit offset calculation
│   ├── generator.py        # Code generation orchestrator
│   └── templates/          # Jinja2 templates for code gen
│       ├── python.jinja2   # Python dataclass template
│       └── base.jinja2     # Shared template components
├── examples/               # Example schemas and usage
│   ├── basic.schema.json   # Simple schema example
│   ├── generated/          # Generated code output
│   └── usage.py            # How to use generated code
├── tests/                  # Test suite
│   ├── test_parser.py
│   ├── test_allocator.py
│   ├── test_encoder.py
│   └── fixtures/           # Test schemas
└── docs/                   # Documentation
    ├── schema_format.md    # JSON schema specification
    └── api.md              # API reference
```

### Structure Rationale

- **bitschema/:** Runtime library enables dynamic schema reading without code generation. Users can `pip install bitschema` and encode/decode data by loading schema JSON at runtime. This is the "runtime encoding" path mentioned in project goals.
- **bitschema_compiler/:** Separate compiler package keeps compile-time dependencies (Jinja2, AST manipulation) isolated from runtime. This enables lightweight runtime library. Provides the "code generation" workflow.
- **templates/:** Template-based code generation is simpler and more maintainable than AST manipulation for generating Python dataclasses. Protocol Buffers uses this approach.
- **Separation enables two workflows:**
  1. Compile-time: `bitschema compile schema.json --output generated.py` → import generated dataclass
  2. Runtime: `schema = Schema.load('schema.json')` → encode data dynamically

## Architectural Patterns

### Pattern 1: Schema Compilation Pipeline

**What:** Multi-stage pipeline transforming schema definition → intermediate representation → output artifacts (schema JSON + generated code).

**When to use:** All schema-driven systems use this pattern. It enables validation and optimization at compile-time while keeping runtime fast.

**Trade-offs:**
- **Pro:** Catches errors early, generates optimized code
- **Pro:** Clear separation of concerns between stages
- **Con:** Requires build step (mitigated by also supporting runtime mode)

**Example:**
```python
# Stage 1: Parse
from bitschema_compiler.parser import SchemaParser
ast = SchemaParser.parse('schema.json')

# Stage 2: Validate
from bitschema_compiler.validator import validate_schema
issues = validate_schema(ast)

# Stage 3: Allocate bits
from bitschema_compiler.allocator import BitAllocator
layout = BitAllocator.compute_layout(ast)

# Stage 4: Generate code
from bitschema_compiler.generator import PythonGenerator
code = PythonGenerator.generate(layout)
```

### Pattern 2: Offset Table for Bit Layout

**What:** Precompute all field bit offsets during schema compilation and store in intermediate schema JSON. Runtime encoder uses offset table for O(1) field access.

**When to use:** When random access to fields is needed. FlatBuffers uses vtables (offset tables) for this purpose.

**Trade-offs:**
- **Pro:** Fast field access at runtime (no calculation needed)
- **Pro:** Deterministic layout enables cross-language compatibility
- **Con:** Schema file is larger (includes offset metadata)

**Example:**
```json
{
  "name": "Packet",
  "total_bits": 32,
  "fields": [
    {"name": "version", "type": "uint", "bits": 4, "offset": 0},
    {"name": "flags", "type": "uint", "bits": 8, "offset": 4},
    {"name": "length", "type": "uint", "bits": 20, "offset": 12}
  ]
}
```

Runtime encoder:
```python
# O(1) field access using precomputed offsets
field_meta = schema.fields['version']
value = extract_bits(data, offset=field_meta['offset'], bits=field_meta['bits'])
```

### Pattern 3: Template-Based Code Generation

**What:** Use templating engine (Jinja2) to generate code from schema rather than building AST programmatically. Protocol Buffers and most modern code generators use this approach.

**When to use:** When generating boilerplate code with consistent structure (dataclasses, encode/decode methods).

**Trade-offs:**
- **Pro:** Templates are easier to read and maintain than AST manipulation
- **Pro:** Non-programmers can modify templates
- **Con:** Less powerful than AST for complex transformations

**Example template (python.jinja2):**
```python
from dataclasses import dataclass
from bitschema import BitSchema

@dataclass
class {{ schema.name }}:
    schema = BitSchema.load('{{ schema.source_file }}')

    {% for field in schema.fields %}
    {{ field.name }}: {{ field.python_type }}
    {% endfor %}

    def encode(self) -> bytes:
        return self.schema.encode({
            {% for field in schema.fields %}
            '{{ field.name }}': self.{{ field.name }},
            {% endfor %}
        })

    @classmethod
    def decode(cls, data: bytes) -> '{{ schema.name }}':
        values = cls.schema.decode(data)
        return cls(**values)
```

### Pattern 4: Two-Level Validation (Compile-time + Runtime)

**What:** Validate schema structure at compile-time (type errors, missing fields) and validate field values at runtime (range checks, constraints).

**When to use:** Always. Defense in depth prevents both schema bugs and data bugs.

**Trade-offs:**
- **Pro:** Catches most errors before runtime
- **Pro:** Runtime validation prevents invalid data from being encoded
- **Con:** Slight runtime overhead (negligible for correctness guarantee)

**Example:**
```python
# Compile-time validation (during schema compilation)
def validate_schema(ast):
    for field in ast.fields:
        if field.type not in VALID_TYPES:
            raise SchemaError(f"Invalid type: {field.type}")
        if field.bits <= 0:
            raise SchemaError(f"Bits must be positive: {field.bits}")
        if field.bits > 64:
            raise SchemaError(f"Bits must be <= 64: {field.bits}")

    # Check for overlapping fields, alignment issues, etc.
    check_layout_conflicts(ast)

# Runtime validation (during encoding)
def encode_field(value, field_schema):
    max_value = (1 << field_schema.bits) - 1
    if value < 0 or value > max_value:
        raise ValueError(
            f"Value {value} out of range for {field_schema.bits}-bit field"
        )
    # Pack the validated value
    return pack_bits(value, field_schema.bits, field_schema.offset)
```

### Pattern 5: Alignment-Aware Bit Allocation

**What:** Bit allocator considers memory alignment rules when assigning offsets. For example, multi-byte fields may need to align on byte boundaries for efficient access.

**When to use:** When targeting systems with alignment requirements (most architectures). This is documented in "The Lost Art of Structure Packing" and Data Structure Alignment patterns.

**Trade-offs:**
- **Pro:** Generated layouts work correctly on all architectures
- **Pro:** Potential performance improvements from aligned access
- **Con:** May waste bits for padding (can be worth it for correctness)

**Example:**
```python
class BitAllocator:
    def compute_layout(self, fields, align_bytes=True):
        offset = 0
        layout = []

        for field in fields:
            # If field is >= 8 bits and crosses byte boundary, add padding
            if align_bytes and field.bits >= 8:
                byte_aligned_offset = (offset + 7) // 8 * 8  # Round up to byte
                if byte_aligned_offset != offset:
                    layout.append({'type': 'padding', 'bits': byte_aligned_offset - offset})
                    offset = byte_aligned_offset

            layout.append({
                'name': field.name,
                'type': field.type,
                'bits': field.bits,
                'offset': offset
            })
            offset += field.bits

        return layout, offset  # Return layout and total bits
```

### Pattern 6: Schema as Single Source of Truth

**What:** JSON/YAML schema file is the authoritative definition. Both generated code and runtime encoder reference the same schema file. Schema evolution is managed by versioning schema files.

**When to use:** Always. This is the core principle of schema-driven systems and ensures consistency.

**Trade-offs:**
- **Pro:** No drift between code generator and runtime behavior
- **Pro:** Schema can be inspected programmatically (introspection)
- **Pro:** Easy to version and track changes
- **Con:** Requires schema file to be distributed with code (or embedded)

**Example:**
```python
# Generated code references schema file
@dataclass
class Packet:
    # Schema is loaded from the same source file used during generation
    _schema = BitSchema.load('packet.schema.json')

    version: int
    flags: int
    length: int

    def encode(self):
        # Uses the same schema that generated this class
        return self._schema.encode({
            'version': self.version,
            'flags': self.flags,
            'length': self.length
        })

# Runtime-only code also uses schema file
schema = BitSchema.load('packet.schema.json')
data = schema.encode({'version': 1, 'flags': 0, 'length': 100})
```

## Data Flow

### Schema Compilation Flow

```
[schema.json file]
    ↓
[SchemaParser] → Parse JSON → AST (in-memory)
    ↓
[SchemaValidator] → Check types, constraints → Validated AST
    ↓
[BitAllocator] → Compute offsets, alignment → Layout with offsets
    ↓
[Generator] → Apply template → Generated Python code
    ↓
[Output files]
    ├─ schema.compiled.json (intermediate schema with offsets)
    └─ generated.py (Python dataclass)
```

### Code Generation Workflow

```
User runs: bitschema compile packet.schema.json --output generated.py

1. Parse: JSON → AST
2. Validate: AST → Check for errors → Raise or continue
3. Allocate: AST → Compute bit offsets → Layout table
4. Enhance: Layout → Add metadata (total_bits, alignment) → Compiled schema
5. Generate: Compiled schema → Apply Jinja2 template → Python code string
6. Write: Python code → generated.py file
7. Write: Compiled schema → packet.schema.compiled.json
```

### Runtime Encoding Flow (Generated Code Path)

```
User code:
    packet = Packet(version=1, flags=0x42, length=1024)
    data = packet.encode()

Flow:
    ↓
[Packet.encode()] → Convert fields to dict
    ↓
[BitSchema.encode()] → Load compiled schema
    ↓
[For each field]:
    ├─ [Validator.validate()] → Check range
    ├─ [Packer.pack_bits()] → Pack to bit position
    └─ [Accumulate to buffer]
    ↓
[Return bytes]
```

### Runtime Encoding Flow (Dynamic Schema Path)

```
User code:
    schema = BitSchema.load('packet.schema.json')
    data = schema.encode({'version': 1, 'flags': 0x42, 'length': 1024})

Flow:
    ↓
[BitSchema.load()] → Parse JSON schema → In-memory schema object
    ↓
[BitSchema.encode()] → Validate dict keys match schema
    ↓
[For each field]:
    ├─ [Validator.validate()] → Check type and range
    ├─ [Packer.pack_bits()] → Pack to bit position using offset
    └─ [Accumulate to buffer]
    ↓
[Return bytes]
```

### Key Data Flows

1. **Schema → Compiled Schema:** One-time compilation adds computed metadata (offsets, total size) to enable fast runtime encoding
2. **Field Values → Bytes:** Encoding uses bitwise operations to pack multiple fields into compact byte representation
3. **Bytes → Field Values:** Decoding extracts bits at known offsets and converts to Python types
4. **Schema Evolution:** New schema versions maintain backward compatibility by preserving field offsets or providing migration logic

## Scaling Considerations

Schema-driven bit-packing systems are primarily CPU-bound (bit manipulation) rather than I/O or memory-bound. Scaling considerations are mostly about schema complexity and data throughput.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **< 100 fields per schema** | Simple in-memory schema representation. Linear scan for field lookup. No optimization needed. |
| **100-1000 fields** | Use dict/hashmap for O(1) field lookup by name. Consider schema compilation to precompute all offsets. |
| **1000+ fields or nested schemas** | Implement schema indexing. Use lazy loading for large schemas. Consider splitting into multiple smaller schemas. |
| **< 1MB/sec throughput** | Pure Python implementation sufficient. Standard library struct module for byte-level operations. |
| **1-100 MB/sec** | Use optimized bit-packing library (bitstruct with C extension). Consider Cython for hot paths. |
| **100+ MB/sec** | Implement core encoder/decoder in C/Rust with Python bindings. Use SIMD instructions for parallel bit operations. |

### Scaling Priorities

1. **First bottleneck: Field lookup overhead**
   - **Symptom:** Encoding time grows linearly with number of fields
   - **Fix:** Precompute field offset table during schema compilation (already in recommended design)
   - **Impact:** O(n) → O(1) field access

2. **Second bottleneck: Python bit manipulation**
   - **Symptom:** High CPU usage during encode/decode for large data volumes
   - **Fix:** Use bitstruct library (has C implementation) or rewrite hot paths in Cython
   - **Impact:** 10-100x speedup for bit packing operations

3. **Third bottleneck: Schema loading**
   - **Symptom:** Slow startup time when loading large schemas repeatedly
   - **Fix:** Cache compiled schemas in memory, or use pickle to serialize Python schema objects
   - **Impact:** Avoid repeated JSON parsing

## Anti-Patterns

### Anti-Pattern 1: Runtime Bit Offset Calculation

**What people do:** Calculate bit offsets during encoding/decoding instead of precomputing during schema compilation.

**Why it's wrong:**
- Wastes CPU time recalculating same offsets repeatedly
- Introduces potential for calculation bugs that only manifest at runtime
- Makes debugging harder (offsets not visible in schema)

**Do this instead:**
Compute offsets during schema compilation and store in intermediate schema JSON. Runtime encoder just reads offsets from schema.

```python
# BAD: Calculate offset on every encode
def encode_field(field_name, value, schema):
    offset = sum(f.bits for f in schema.fields if f.name < field_name)  # Recalculating!
    pack_bits(value, schema.fields[field_name].bits, offset)

# GOOD: Use precomputed offset
def encode_field(field_name, value, schema):
    field = schema.fields[field_name]
    pack_bits(value, field.bits, field.offset)  # Offset precomputed
```

### Anti-Pattern 2: Mixing Schema Definition with Business Logic

**What people do:** Put validation rules, defaults, or transformation logic in schema files instead of application code.

**Why it's wrong:**
- Schema should describe data structure only (single responsibility)
- Business logic changes more frequently than data structure
- Makes schema files language-specific (defeats cross-language goal)
- Hard to test business logic embedded in schema

**Do this instead:**
Keep schema purely structural. Put validation and business logic in application layer.

```python
# BAD: Validation in schema
{
  "name": "User",
  "fields": [
    {"name": "age", "type": "uint", "bits": 8, "min": 18, "max": 120}  # Business rule!
  ]
}

# GOOD: Schema describes structure only
# schema.json
{
  "name": "User",
  "fields": [
    {"name": "age", "type": "uint", "bits": 8}  # Just structure
  ]
}

# Application code
def create_user(age):
    if age < 18 or age > 120:  # Business logic in app
        raise ValueError("Age must be 18-120")
    return User(age=age)
```

### Anti-Pattern 3: Implicit Field Ordering Dependencies

**What people do:** Rely on alphabetical field ordering or declaration order in ways that break when schema is modified.

**Why it's wrong:**
- Fragile: Adding a field breaks all existing encoded data
- Debugging nightmare when data becomes unreadable
- Defeats schema evolution goals

**Do this instead:**
Use explicit field numbering (like Protocol Buffers) or preserve field order and only allow appending new fields.

```python
# BAD: Implicit ordering
{
  "fields": [
    {"name": "version", "bits": 4},  # What if we add a field before this?
    {"name": "flags", "bits": 8}
  ]
}

# GOOD: Explicit offsets or field numbers
{
  "fields": [
    {"name": "version", "field_number": 1, "bits": 4, "offset": 0},
    {"name": "flags", "field_number": 2, "bits": 8, "offset": 4}
  ]
}
# New field added later doesn't break existing data
```

### Anti-Pattern 4: Byte-Misaligned Multi-Byte Fields

**What people do:** Pack multi-byte integers across byte boundaries without considering alignment.

**Why it's wrong:**
- Unaligned access is slow on many CPUs (x86 allows but penalizes; ARM may fault)
- Debugging binary data is harder when fields don't align to bytes
- Breaks assumptions of tools that expect byte-aligned data

**Do this instead:**
Add explicit padding bits to align multi-byte fields on byte boundaries.

```python
# BAD: 16-bit field starts at bit 5 (crosses byte boundary)
{
  "fields": [
    {"name": "flags", "bits": 5, "offset": 0},      # 5 bits
    {"name": "count", "bits": 16, "offset": 5}      # Spans bytes 0-2 awkwardly
  ]
}

# GOOD: Add padding to align 16-bit field
{
  "fields": [
    {"name": "flags", "bits": 5, "offset": 0},      # 5 bits
    {"name": "_padding", "bits": 3, "offset": 5},   # 3 bits padding
    {"name": "count", "bits": 16, "offset": 8}      # Starts at byte 1
  ]
}
```

### Anti-Pattern 5: Encoding Schema Metadata in Every Message

**What people do:** Include schema version, field count, or type information in every encoded message.

**Why it's wrong:**
- Wastes space (defeats purpose of bit packing for compactness)
- Schema is already known at decode time (via schema file)
- Self-describing formats (JSON, XML) exist if you need this

**Do this instead:**
Encode only data fields. Store schema separately. If versioning is needed, use schema version in filename or single version field.

```python
# BAD: Encoding schema info repeatedly
message = {
  'schema_version': 1,      # 32 bits wasted
  'field_count': 3,         # 32 bits wasted
  'data': actual_data
}

# GOOD: Just encode the data
message = actual_data  # Decoder already has schema file

# If versioning needed, single version field is enough
message = {
  'v': 1,           # 4-8 bits (can encode many versions)
  'data': actual_data
}
```

## Integration Points

### External Tools/Libraries

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Python struct module** | Use for byte-level packing fallback | Standard library, no dependencies. Limited to byte alignment. |
| **bitstruct library** | Use for true bit-level packing | Has C extension for performance. Recommended for production. |
| **Jinja2** | Template engine for code generation | Industry standard. Easy to maintain templates. |
| **pytest** | Testing framework | Test schema parsing, bit allocation, round-trip encode/decode. |
| **JSON Schema** | Optional schema validation | Can validate BitSchema JSON files against meta-schema. |
| **mypy** | Type checking generated code | Ensure generated Python code is type-safe. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Parser ↔ Validator** | AST (Python dict/object) | Parser produces AST, validator consumes and checks it. Clean separation. |
| **Validator ↔ Allocator** | Validated AST | Allocator assumes AST is already validated (types correct, no conflicts). |
| **Allocator ↔ Generator** | Layout table (list of field metadata) | Generator consumes layout to fill templates. Doesn't need raw AST. |
| **Compiler ↔ Runtime** | Compiled schema JSON file | File I/O boundary. JSON is universal format both sides understand. |
| **Generated Code ↔ Runtime Library** | Method calls (encode/decode API) | Generated dataclass calls runtime library methods. Loose coupling. |
| **Encoder ↔ Packer** | Field value + metadata → bytes | Encoder orchestrates; Packer does low-level bit manipulation. Single responsibility. |

## Build Order Implications

Based on dependency analysis, recommended implementation order:

### Phase 1: Core Data Model (Foundation)
Build these first as all other components depend on them:

1. **Schema Type System** (`types.py`): Define supported types (uint, int, bool, etc.)
2. **Bit Packer** (`packer.py`): Low-level bit manipulation functions
3. **Simple Schema Representation**: Python class to hold parsed schema in memory

**Rationale:** These are leaf dependencies. Nothing depends on downstream components.

### Phase 2: Schema Processing Pipeline
Build the compile-time pipeline:

4. **Schema Parser** (`parser.py`): Parse JSON → AST
5. **Schema Validator** (`validator.py`): Validate AST → Errors/warnings
6. **Bit Allocator** (`allocator.py`): AST → Layout with offsets

**Rationale:** Linear dependency chain. Each component builds on previous.

### Phase 3: Runtime Encoding (MVP)
Build enough to encode/decode without code generation:

7. **Schema Loader** (`schema.py`): Load compiled schema from JSON
8. **Encoder/Decoder** (`encoder.py`): High-level API using schema + packer
9. **Field Validator** (`validator.py` runtime): Runtime value validation

**Rationale:** This completes the "runtime encoding" workflow. Users can now use BitSchema without code generation.

### Phase 4: Code Generation
Add the optional code generation workflow:

10. **Code Generator** (`generator.py`): Orchestrate template rendering
11. **Python Template** (`templates/python.jinja2`): Generate dataclasses
12. **CLI Tool**: Command-line interface for `bitschema compile`

**Rationale:** Code generation is optional feature. Runtime encoding already works without it.

### Phase 5: Schema Evolution & Advanced Features
Add features for production use:

13. **Schema Versioning**: Support multiple schema versions
14. **Backward Compatibility**: Read old data with new schema
15. **Nested Schemas**: Support for composite types
16. **Array/Repeated Fields**: Support for variable-length data

**Rationale:** These are enhancements that don't block core functionality.

### Dependency Graph

```
Low-level (no dependencies):
  types.py
  packer.py

Parse/Validate (depends on types):
  parser.py → types.py
  validator.py → types.py, parser.py

Layout (depends on validated schema):
  allocator.py → types.py, validator.py

Runtime (depends on layout + packer):
  schema.py → types.py, allocator.py
  encoder.py → schema.py, packer.py, validator.py

Code generation (depends on layout):
  generator.py → allocator.py
  templates/ → (templates have no code dependencies)

CLI (depends on everything):
  cli.py → parser.py, validator.py, allocator.py, generator.py
```

This build order enables **incremental development with testable milestones** at each phase.

## Sources

### Official Documentation (HIGH confidence)
- [Protocol Buffers Documentation](https://protobuf.dev)
- [Protocol Buffers Overview](https://protobuf.dev/overview/)
- [Python struct module](https://docs.python.org/3/library/struct.html)
- [bitstruct documentation](https://bitstruct.readthedocs.io/)

### Authoritative Comparisons (HIGH confidence)
- [Cap'n Proto: Comparison with FlatBuffers and SBE](https://capnproto.org/news/2014-06-17-capnproto-flatbuffers-sbe.html)

### Architecture Patterns (MEDIUM confidence)
- [Protocol Buffers in System Design - GeeksforGeeks](https://www.geeksforgeeks.org/system-design/protocol-buffer-protobuf-in-system-design/)
- [Data Serialization Formats - lik.ai](https://lik.ai/blog/data-serialization-formats/)
- [Schema Registry Serialization - Solace](https://docs.solace.com/Schema-Registry/schema-registry-serdes.htm)
- [Kafka Schema Registry Best Practices - AutoMQ](https://www.automq.com/blog/kafka-schema-registry-learn-use-best-practices)

### Code Generation Patterns (MEDIUM confidence)
- [Code Generation Agents: Architecture - Grizzly Peak Software](https://www.grizzlypeaksoftware.com/library/code-generation-agents-architecture-and-implementation-cywpmevh)
- [TypeScript Code Generator: Templates vs AST - Medium](https://medium.com/singapore-gds/writing-a-typescript-code-generator-templates-vs-ast-ab391e5d1f5e)
- [Metalama.Framework 2026 - NuGet](https://www.nuget.org/packages/Metalama.Framework)

### Bit-Field & Alignment (HIGH confidence)
- [Data Structure Alignment - Wikipedia](https://en.wikipedia.org/wiki/Data_structure_alignment)
- [The Lost Art of Structure Packing](http://www.catb.org/esr/structure-packing/)
- [Memory Alignment - Microsoft Learn](https://learn.microsoft.com/en-us/cpp/cpp/alignment-cpp-declarations?view=msvc-170)

### Python Libraries (HIGH confidence)
- [bitstruct PyPI](https://pypi.org/project/bitstruct/)
- [bitstring documentation](https://bitstring.readthedocs.io/en/stable/)
- [construct library](https://construct.readthedocs.io/en/latest/bitwise.html)

### 2026 Trends (MEDIUM confidence)
- [Common Serialization Formats Explained 2026 - Business Blog Hub](https://www.businessblogshub.com/2026/02/common-serialization-formats-explained-json-xml-binary/)
- [Modern HTTP Stack in 2026 - Hemaks](https://hemaks.org/posts/modern-http-stack-in-2026-http3-grpc-websockets-and-when-to-use-what/)
- [8 Data Engineering Design Patterns 2026 - ISMTech](https://www.ismtech.net/it-topics-trends-th/8-data-engineering-design-patterns-you-must-know-in-2026/)

---
*Architecture research for: BitSchema schema-driven bit-packing system*
*Researched: 2026-02-19*
