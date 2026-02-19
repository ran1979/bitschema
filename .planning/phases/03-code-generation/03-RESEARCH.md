# Phase 3: Code Generation - Research

**Researched:** 2026-02-19
**Domain:** Python code generation, dataclass generation, JSON Schema export, visualization
**Confidence:** HIGH

## Summary

Phase 3 requires generating static Python dataclasses from BitSchema schemas, exporting JSON Schema format, and creating bit layout visualizations. The Python ecosystem has mature tools for this domain, with clear patterns emerging for code generation.

**Key findings:**
- String templating (Jinja2 or f-strings with textwrap) is the standard approach for generating readable Python code
- Python's ast module with ast.unparse() provides AST-based code generation but is overkill for dataclass generation
- Ruff (or Black) should be used for formatting generated code to ensure PEP 8 compliance
- JSON Schema Draft 2020-12 is the current standard, with full support in Python libraries
- Multiple mature libraries exist for ASCII table visualization (table2ascii, prettytable, tabulate)

**Primary recommendation:** Use string templating with Jinja2 for code generation, format output with Ruff/Black, generate JSON Schema Draft 2020-12 with standard keywords, and use tabulate or prettytable for bit layout visualization.

## Standard Stack

The established libraries/tools for Python code generation:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.x | Template-based code generation | Industry standard for code generators, used by major tools (datamodel-code-generator), excellent control over formatting |
| Python textwrap | stdlib | String formatting and indentation | Built-in, reliable for indentation control, zero dependencies |
| Python ast | stdlib | AST manipulation and unparsing | Official Python module, comprehensive type annotation support, validate generated code |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Ruff | 0.8+ | Code formatting | Format generated code (30x faster than Black, Black-compatible) |
| Black | 24.x | Alternative code formatter | If Ruff not available, widely adopted standard |
| tabulate | 0.9+ | ASCII table generation | Bit layout visualization with multiple output formats |
| prettytable | 3.x | ASCII table generation | Alternative for table visualization |
| table2ascii | 1.x | Modern table library | Type-safe, Discord-compatible markdown |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 templates | AST with ast.unparse() | AST is more complex, harder to debug, overkill for straightforward dataclass generation. Better for complex transformations. |
| String templates | datamodel-code-generator library | Full library dependency vs simple templates. We need custom logic for encode/decode methods specific to bit-packing. |
| Ruff | autopep8 | autopep8 only fixes PEP 8 violations, doesn't ensure uniform formatting. Ruff/Black enforce consistent style. |
| JSON dict construction | Pydantic model_json_schema | Our schema is simpler than Pydantic models. Direct construction gives full control over JSON Schema output format. |

**Installation:**
```bash
# Core dependencies (already in project)
pip install jinja2>=3.1

# Dev dependencies for formatting (optional)
pip install ruff>=0.8  # Or black>=24.0

# For visualization
pip install tabulate>=0.9
```

## Architecture Patterns

### Recommended Project Structure

```
bitschema/
├── codegen.py           # Code generation orchestrator
├── templates/           # Jinja2 templates (optional directory)
│   └── dataclass.py.j2  # Dataclass template
├── jsonschema.py        # JSON Schema export
└── visualization.py     # Bit layout visualization

tests/
├── test_codegen.py      # Generated code tests
├── test_jsonschema.py   # JSON Schema export tests
└── test_visualization.py # Visualization tests
```

### Pattern 1: String Template-Based Generation

**What:** Use Jinja2 templates or f-strings with textwrap.dedent() to generate Python code
**When to use:** Generating dataclasses with predictable structure (like ours)
**Example:**

```python
# Source: Common pattern from datamodel-code-generator and similar tools
from textwrap import dedent, indent

def generate_dataclass(schema_name: str, fields: list[tuple[str, str, str]]) -> str:
    """Generate dataclass using f-strings and textwrap."""

    # Generate field definitions
    field_defs = []
    for name, type_hint, default in fields:
        if default:
            field_defs.append(f"{name}: {type_hint} = {default}")
        else:
            field_defs.append(f"{name}: {type_hint}")

    fields_str = indent("\n".join(field_defs), "    ")

    code = dedent(f"""\
        from dataclasses import dataclass

        @dataclass
        class {schema_name}:
            '''Generated dataclass for {schema_name} schema.'''
            {fields_str}
        """)

    return code
```

Alternative with Jinja2:
```python
# Source: https://jinja.palletsprojects.com/en/stable/templates/
from jinja2 import Template

template = Template('''
from dataclasses import dataclass

@dataclass
class {{ class_name }}:
    """{{ docstring }}"""
{% for field in fields %}
    {{ field.name }}: {{ field.type_hint }}{{ " = " + field.default if field.default else "" }}
{% endfor %}

    def encode(self) -> int:
        """Encode to 64-bit integer."""
        # Generated encoding logic
        pass
''')

code = template.render(class_name="User", docstring="...", fields=[...])
```

### Pattern 2: Format Generated Code

**What:** Always format generated code with Black or Ruff to ensure PEP 8 compliance
**When to use:** After generating any Python code string
**Example:**

```python
# Source: https://docs.astral.sh/ruff/formatter/
import subprocess
from pathlib import Path

def format_generated_code(code: str) -> str:
    """Format code using Ruff (or fall back to Black)."""
    try:
        # Try Ruff first (30x faster than Black)
        result = subprocess.run(
            ["ruff", "format", "-"],
            input=code.encode(),
            capture_output=True,
            check=True
        )
        return result.stdout.decode()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fall back to Black
        result = subprocess.run(
            ["black", "-", "--quiet"],
            input=code.encode(),
            capture_output=True,
            check=True
        )
        return result.stdout.decode()
```

### Pattern 3: JSON Schema Generation

**What:** Construct JSON Schema Draft 2020-12 compliant dict
**When to use:** Exporting schema for ecosystem integration
**Example:**

```python
# Source: https://json-schema.org/draft/2020-12/json-schema-core
def generate_json_schema(schema_name: str, fields: list) -> dict:
    """Generate JSON Schema Draft 2020-12."""

    json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://example.com/schemas/{schema_name.lower()}.json",
        "type": "object",
        "title": schema_name,
        "properties": {},
        "required": [],
        "additionalProperties": False
    }

    for field in fields:
        # Build field schema based on type
        if field.type == "boolean":
            json_schema["properties"][field.name] = {"type": "boolean"}
        elif field.type == "integer":
            json_schema["properties"][field.name] = {
                "type": "integer",
                "minimum": field.min,
                "maximum": field.max
            }
        elif field.type == "enum":
            json_schema["properties"][field.name] = {
                "type": "string",
                "enum": field.values
            }

        # Add to required if not nullable
        if not field.nullable:
            json_schema["required"].append(field.name)

    return json_schema
```

### Pattern 4: Bit Layout Visualization

**What:** Generate ASCII table or markdown table showing bit positions
**When to use:** For documentation and debugging bit layouts
**Example:**

```python
# Source: https://pypi.org/project/tabulate/
from tabulate import tabulate

def visualize_bit_layout(layouts: list[FieldLayout]) -> str:
    """Generate ASCII table of bit layout."""

    table_data = []
    for layout in layouts:
        # Build row: [field_name, type, offset, bits, range]
        bit_range = f"{layout.offset}:{layout.offset + layout.bits - 1}"

        # Add constraints info
        constraints = ""
        if layout.type == "integer":
            min_val = layout.constraints.get("min", "")
            max_val = layout.constraints.get("max", "")
            constraints = f"[{min_val}..{max_val}]"
        elif layout.type == "enum":
            values = layout.constraints.get("values", [])
            constraints = f"{len(values)} values"

        table_data.append([
            layout.name,
            layout.type,
            bit_range,
            layout.bits,
            constraints
        ])

    headers = ["Field", "Type", "Bit Range", "Bits", "Constraints"]

    # Generate ASCII table
    ascii_table = tabulate(table_data, headers=headers, tablefmt="grid")

    # Also generate markdown
    md_table = tabulate(table_data, headers=headers, tablefmt="github")

    return f"ASCII:\n{ascii_table}\n\nMarkdown:\n{md_table}"
```

### Pattern 5: Type Hints for Generated Code

**What:** Use modern Python 3.10+ union syntax (| instead of Union/Optional)
**When to use:** All generated dataclass fields with type annotations
**Example:**

```python
# Source: https://docs.python.org/3/library/typing.html
# Modern Python 3.10+ syntax for type hints

# Nullable field
field_name: int | None = None

# Non-nullable
field_name: int

# For backward compatibility with Python 3.9:
from typing import Optional
field_name: Optional[int] = None
```

### Anti-Patterns to Avoid

- **Hand-rolling indentation:** Use textwrap.indent() or Jinja2 instead of manual space counting - prevents indentation bugs
- **Generating unformatted code:** Always format with Ruff/Black - ensures consistency and catches syntax errors
- **AST for simple templates:** ast.unparse() is overkill for dataclass generation - use string templates for readability
- **Type comments vs annotations:** Don't use `# type:` comments, use proper Python 3.10+ type annotations with `:` syntax
- **Hardcoded paths in tests:** Use pathlib.Path and relative paths for generated output tests

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Code formatting | Custom indentation logic | Ruff or Black | Handles edge cases (line length, operator spacing, string formatting), PEP 8 compliant |
| ASCII table layout | Manual string concatenation | tabulate or prettytable | Handles alignment, borders, multiple formats (markdown, grid, etc.) |
| Template rendering | String concatenation with += | Jinja2 or textwrap.dedent() | Prevents escaping bugs, handles indentation, more maintainable |
| JSON Schema validation | Custom dict validation | jsonschema library | Validates against spec, handles $ref, catches edge cases |
| Atomic file writes | Direct open/write | Use temp file + os.replace() pattern | Prevents file corruption on crash, atomic operation |

**Key insight:** Code generation has many edge cases (escaping, indentation, special characters, line length). Use battle-tested libraries rather than reimplementing these. The complexity comes from handling all the edge cases correctly.

## Common Pitfalls

### Pitfall 1: Indentation Errors in Generated Code

**What goes wrong:** Generated Python code has mixed tabs/spaces, incorrect indentation levels, or inconsistent indentation
**Why it happens:** Manual string concatenation with hardcoded spaces, forgetting to account for nested blocks
**How to avoid:**
- Use textwrap.dedent() to remove leading whitespace, then textwrap.indent() to add consistent indentation
- Use Jinja2 templates which handle indentation automatically
- Always format final output with Ruff/Black to catch indentation issues
**Warning signs:** IndentationError when importing generated code, code looks correct but fails to parse

### Pitfall 2: Invalid Python Identifiers in Generated Names

**What goes wrong:** Schema field names become invalid Python identifiers (e.g., "user-role" → "user-role" is not valid Python)
**Why it happens:** Schema allows more characters than Python identifiers (hyphens, spaces, starting with digits)
**How to avoid:**
- Validate field names are valid Python identifiers during schema loading (we already do this in models.py)
- Document that field names must be valid Python identifiers
- If transformation is needed, use str.isidentifier() to validate
**Warning signs:** SyntaxError when parsing generated code, NameError at runtime

### Pitfall 3: Type Annotation Syntax Errors

**What goes wrong:** Generated type hints use deprecated syntax (Union[X, None] instead of X | None) or missing imports
**Why it happens:** Not tracking Python version requirements, forgetting to import from typing module
**How to avoid:**
- For Python 3.10+, use native | syntax (int | None)
- For Python 3.9 compatibility, import from typing and use Optional[int]
- Test generated code imports and validates with mypy or pyright
**Warning signs:** ImportError for typing, SyntaxError on | in Python 3.9

### Pitfall 4: File Corruption During Write

**What goes wrong:** Generated file is empty or partial if program crashes during write
**Why it happens:** Writing directly to target file without atomic operation
**How to avoid:**
- Write to temporary file first
- Use os.replace() to atomically move temp file to target (available Python 3.3+)
- Pattern: write to .tmp, then replace original
**Warning signs:** Empty generated files after crashes, partial file content

### Pitfall 5: Missing or Incorrect Docstrings

**What goes wrong:** Generated code has no docstrings or they contain unescaped quotes/newlines
**Why it happens:** Forgetting to escape special characters in docstring content, not using triple-quoted strings
**How to avoid:**
- Always use triple-quoted strings for docstrings ("""...""")
- Escape any triple-quotes in docstring content
- Include schema metadata in docstrings (field constraints, bit positions)
**Warning signs:** SyntaxError in generated code, missing IDE documentation hints

### Pitfall 6: JSON Schema Spec Non-Compliance

**What goes wrong:** Generated JSON Schema is rejected by validators or tools
**Why it happens:** Missing required fields ($schema, type), using wrong draft version, incorrect $id format
**How to avoid:**
- Always include "$schema" with full URI (https://json-schema.org/draft/2020-12/schema)
- Include type: "object" for object schemas
- Use valid URI for $id field
- Test generated schema with jsonschema library validator
**Warning signs:** Schema rejected by validators, tools can't parse exported schema

## Code Examples

Verified patterns from official sources:

### Complete Dataclass Generation (String Template)

```python
# Source: Common pattern from datamodel-code-generator approach
from textwrap import dedent, indent

def generate_field_type_hint(field_def) -> str:
    """Generate type hint for a field."""
    if field_def.type == "bool":
        type_hint = "bool"
    elif field_def.type == "int":
        type_hint = "int"
    elif field_def.type == "enum":
        type_hint = "str"  # Or use Literal["val1", "val2"]
    else:
        raise ValueError(f"Unknown field type: {field_def.type}")

    # Add None for nullable
    if field_def.nullable:
        type_hint = f"{type_hint} | None"

    return type_hint

def generate_dataclass_code(schema, layouts) -> str:
    """Generate complete dataclass with encode/decode methods."""

    # Build field definitions
    field_lines = []
    for field_name, field_def in schema.fields.items():
        type_hint = generate_field_type_hint(field_def)

        # Add default for nullable fields
        if field_def.nullable:
            field_lines.append(f"{field_name}: {type_hint} = None")
        else:
            field_lines.append(f"{field_name}: {type_hint}")

    fields_str = indent("\n".join(field_lines), "    ")

    # Generate encode method (simplified - real version uses encoder.py logic)
    encode_body = "# Encode logic here\npass"
    encode_str = indent(encode_body, "        ")

    # Generate decode method (simplified)
    decode_body = "# Decode logic here\npass"
    decode_str = indent(decode_body, "        ")

    code = dedent(f'''\
        """Generated by BitSchema from {schema.name} schema."""
        from dataclasses import dataclass

        @dataclass
        class {schema.name}:
            """BitSchema dataclass: {schema.name}

            Packs {len(schema.fields)} fields into {sum(l.bits for l in layouts)} bits.

            Fields:
        {indent(chr(10).join(f"    {n}: {generate_field_type_hint(f)}" for n, f in schema.fields.items()), "    ")}
            """
        {fields_str}

            def encode(self) -> int:
                """Encode to 64-bit integer."""
        {encode_str}

            @classmethod
            def decode(cls, value: int) -> "{schema.name}":
                """Decode from 64-bit integer."""
        {decode_str}
        ''')

    return code
```

### Atomic File Write

```python
# Source: https://discuss.python.org/t/atomic-writes-to-files/24374
import os
import tempfile
from pathlib import Path

def write_generated_file(target_path: Path, content: str) -> None:
    """Write file atomically to prevent corruption."""

    # Create temp file in same directory (ensures same filesystem)
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(
        dir=target_dir,
        prefix=".tmp_",
        suffix=target_path.suffix,
        text=True
    )

    try:
        # Write content
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)

        # Atomically replace target file
        # os.replace() is atomic on POSIX and Windows (Python 3.3+)
        os.replace(temp_path, target_path)
    except:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise
```

### Validate Generated Code

```python
# Source: https://docs.python.org/3/library/ast.html
import ast

def validate_generated_code(code: str) -> bool:
    """Validate generated Python code is syntactically correct."""
    try:
        # Parse to AST
        ast.parse(code)

        # Optionally, compile to bytecode to catch more errors
        compile(code, '<generated>', 'exec')

        return True
    except SyntaxError as e:
        print(f"Syntax error in generated code: {e}")
        return False
```

### JSON Schema with All Required Fields

```python
# Source: https://json-schema.org/draft/2020-12/json-schema-core
def generate_json_schema_export(schema, layouts) -> dict:
    """Generate JSON Schema Draft 2020-12 compliant schema."""

    json_schema = {
        # Required: Identify the dialect
        "$schema": "https://json-schema.org/draft/2020-12/schema",

        # Optional but recommended: Canonical URI
        "$id": f"https://example.com/schemas/{schema.name.lower()}.schema.json",

        # Required: Type of root
        "type": "object",

        # Metadata
        "title": schema.name,
        "description": f"BitSchema-generated schema for {schema.name}",

        # Properties
        "properties": {},

        # Non-nullable fields are required
        "required": [],

        # Don't allow additional properties
        "additionalProperties": False,

        # Custom metadata (not part of standard, but allowed)
        "x-bitschema-version": "1",
        "x-bitschema-total-bits": sum(layout.bits for layout in layouts)
    }

    # Build properties
    for field_name, field_def in schema.fields.items():
        prop = {}

        if isinstance(field_def, BoolFieldDefinition):
            prop["type"] = "boolean"

        elif isinstance(field_def, IntFieldDefinition):
            if field_def.nullable:
                prop["type"] = ["integer", "null"]
            else:
                prop["type"] = "integer"

            if field_def.min is not None:
                prop["minimum"] = field_def.min
            if field_def.max is not None:
                prop["maximum"] = field_def.max

        elif isinstance(field_def, EnumFieldDefinition):
            if field_def.nullable:
                prop["type"] = ["string", "null"]
                prop["enum"] = field_def.values + [None]
            else:
                prop["type"] = "string"
                prop["enum"] = field_def.values

        json_schema["properties"][field_name] = prop

        # Add to required if not nullable
        if not field_def.nullable:
            json_schema["required"].append(field_name)

    return json_schema
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Union[X, None] | X \| None | Python 3.10 (2021) | Simpler syntax, no typing import needed for basic types |
| String concatenation for code gen | Jinja2 templates or textwrap | ~2015+ | More maintainable, fewer escaping bugs |
| Black for formatting | Ruff (Black-compatible) | 2023-2024 | 30x speed improvement, unified toolchain |
| JSON Schema Draft 7 | JSON Schema Draft 2020-12 | 2020 | Better validation keywords, $dynamicRef, prefixItems |
| os.rename() | os.replace() | Python 3.3 (2012) | Atomic on Windows too, not just POSIX |

**Deprecated/outdated:**
- Type comments (`# type: int`): Use proper type annotations with `:` syntax (PEP 526)
- ast.literal_eval() for code generation: Use ast.unparse() instead (added Python 3.9)
- format() string method: Use f-strings for code templates (more readable, Python 3.6+)
- JSON Schema Draft 4/7: Use Draft 2020-12 for new schemas

## Open Questions

Things that couldn't be fully resolved:

1. **Should we use Jinja2 or plain f-strings for templates?**
   - What we know: Jinja2 is industry standard for code generators, but adds dependency. f-strings with textwrap are zero-dependency.
   - What's unclear: Our templates are simple - is Jinja2 overkill?
   - Recommendation: Start with f-strings + textwrap for simplicity. Migrate to Jinja2 if templates become complex or we need features like template inheritance.

2. **Should we format generated code or provide unformatted output?**
   - What we know: Ruff/Black ensure consistent, PEP 8 compliant output. But requires external dependency or subprocess call.
   - What's unclear: Should formatting be mandatory or optional?
   - Recommendation: Always format for better user experience. Make formatter optional (try Ruff → Black → unformatted) to avoid hard dependency.

3. **Python version support for type hints?**
   - What we know: Project requires Python 3.10+. Union syntax (|) is available in 3.10+.
   - What's unclear: Should we support Python 3.9 for wider compatibility?
   - Recommendation: Use Python 3.10+ syntax (X | None) since pyproject.toml already specifies `requires-python = ">=3.10"`. This is consistent with project requirements.

4. **JSON Schema $id format?**
   - What we know: $id should be a valid URI, preferably absolute. But our schemas don't have a canonical URL.
   - What's unclear: What domain/URL should we use? Or should $id be omitted?
   - Recommendation: Make $id optional. If provided, validate it's a valid URI. Document that users should override with their own domain.

## Sources

### Primary (HIGH confidence)

- [Python ast module documentation](https://docs.python.org/3/library/ast.html) - ast.unparse() capabilities and type annotations
- [JSON Schema Draft 2020-12 Core Specification](https://json-schema.org/draft/2020-12/json-schema-core) - Required fields and keywords
- [Python typing module documentation](https://docs.python.org/3/library/typing.html) - Type hints and union syntax
- [PEP 604 - Union Types](https://peps.python.org/pep-0604/) - Modern | syntax for unions
- [Ruff Formatter Documentation](https://docs.astral.sh/ruff/formatter/) - Black-compatible formatting

### Secondary (MEDIUM confidence)

- [datamodel-code-generator GitHub](https://github.com/koxudaxi/datamodel-code-generator/) - Industry standard for code generation from schemas (verified approach)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/en/stable/templates/) - Template engine patterns
- [tabulate PyPI](https://pypi.org/project/tabulate/) - ASCII table generation library
- [Python Dataclasses: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/python-dataclasses-guide) - Best practices for dataclass generation
- [Atomic File Writes Discussion](https://discuss.python.org/t/atomic-writes-to-files/24374) - os.replace() pattern

### Tertiary (LOW confidence)

- [Click vs argparse comparison](https://www.pythonsnacks.com/p/click-vs-argparse-python) - CLI library comparison (if we add CLI)
- [Python Type Hints Complete Guide 2026](https://devtoolbox.dedyn.io/blog/python-type-hints-complete-guide) - Modern type hint patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Python documentation and widely adopted libraries (Jinja2, Ruff)
- Architecture: HIGH - Patterns verified in official docs and production code generators
- Pitfalls: HIGH - Common errors documented in official discussions and error guides

**Research date:** 2026-02-19
**Valid until:** 60 days (stable ecosystem, Python 3.10+ is mature, JSON Schema 2020-12 is current standard)

**Key constraints from prior decisions:**
- Python 3.10+ requirement (enables | syntax for unions)
- Pydantic v2 for schema models (leverage existing validation)
- Generated code must produce identical results to runtime encoder/decoder
- 64-bit integer limit enforced at schema level
