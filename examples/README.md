# BitSchema Examples

This directory contains example schema definitions demonstrating various BitSchema features.

## Example Schemas

### user.json / user.yaml
User profile schema demonstrating:
- Integer fields with bit constraints (age: 7 bits)
- Boolean fields (active)
- Enum fields (role with 4 values)
- Nullable fields (score)
- Total: 27 bits

### sensor_reading.json
IoT sensor data schema showing:
- Signed integers for temperature (-2048 to 2047)
- Unsigned integers for humidity (0-100%)
- Boolean status flags
- Enum for device status
- 32-bit timestamp offset
- Total: 54 bits

### compact_flags.yaml
Bit-efficient feature flags demonstrating:
- Multiple boolean flags (6 total)
- Small enums (priority: 4 values = 2 bits)
- Compact integer fields (user_tier: 4 bits)
- Total: 12 bits (fits in 2 bytes!)

## Loading Examples

### From Python

```python
from bitschema import load_schema

# Load from JSON
schema = load_schema("examples/user.json")
print(f"Schema: {schema.name}")
print(f"Total bits: {schema.calculate_total_bits()}")

# Load from YAML
schema = load_schema("examples/user.yaml")

# Access fields
for field_name, field_def in schema.fields.items():
    print(f"  {field_name}: {field_def.type}")
```

### Using the Schema

```python
# After loading, the schema validates:
# - Field bit allocations fit in 64-bit limit
# - Min/max constraints are representable
# - Enum values are unique
# - Field names are valid identifiers

# Check total size
bits = schema.calculate_total_bits()
bytes_needed = (bits + 7) // 8
print(f"Packed size: {bytes_needed} bytes")
```

## Schema Format

All schemas follow the BitSchema v1 format:

```json
{
  "version": "1",
  "name": "SchemaName",
  "fields": {
    "field_name": {
      "type": "int|bool|enum",
      // Type-specific properties
    }
  }
}
```

### Field Types

**Integer (`int`):**
```json
{
  "type": "int",
  "bits": 8,           // Required: 1-64
  "signed": false,     // Optional: default false
  "nullable": false,   // Optional: default false
  "min": 0,           // Optional: runtime constraint
  "max": 255          // Optional: runtime constraint
}
```

**Boolean (`bool`):**
```json
{
  "type": "bool",
  "nullable": false   // Optional: default false
}
```

**Enum (`enum`):**
```json
{
  "type": "enum",
  "values": ["a", "b", "c"],  // Required: 1-255 unique strings
  "nullable": false           // Optional: default false
}
```

## Bit Calculations

BitSchema automatically calculates minimum bits required:

- **Boolean**: 1 bit
- **Integer**: Specified in `bits` field
- **Enum**: `log2(num_values)` rounded up
  - 2 values = 1 bit
  - 3-4 values = 2 bits
  - 5-8 values = 3 bits
  - etc.
- **Nullable**: +1 presence bit per nullable field

## Validation

All schemas are validated on load:
- Total bits must not exceed 64
- Integer min/max must fit in allocated bits
- Enum values must be unique and non-empty
- Field names must be valid Python identifiers
