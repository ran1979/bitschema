# Pitfalls Research

**Domain:** Bit-packing and serialization libraries
**Researched:** 2026-02-19
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Silent Integer Truncation and Overflow

**What goes wrong:**
Values that exceed the allocated bit width are silently truncated or wrapped around without any warning or error. For example, trying to pack the value 256 into an 8-bit field silently becomes 0, or storing -129 in an int8_t wraps to 127. This leads to data corruption that may not be detected until production.

**Why it happens:**
Developers assume that validation happens automatically, or they rely on language-level type checking which doesn't understand bit-level constraints. The bitwise operations (masks, shifts) silently discard overflowing bits by design. Many libraries prioritize performance over safety and skip validation.

**How to avoid:**
- Validate ALL values at encode time before bit operations occur
- Use explicit range checks: `if (value > max_for_bits(n)) throw`
- Provide clear error messages: "Value 256 exceeds 8-bit maximum of 255" not "validation failed"
- Consider saturation mode as an explicit opt-in (clamp to max) rather than default
- Add compile-time checks where possible using template constraints

**Warning signs:**
- Test data works but production values fail mysteriously
- Round-trip tests pass with small numbers but fail with edge cases
- Different behavior between debug and release builds
- Data corruption appears non-deterministic (depends on input values)

**Phase to address:**
Core validation layer (Phase 1) - must be foundational before any encoding logic

---

### Pitfall 2: Bit Shift Undefined Behavior

**What goes wrong:**
Bit shift operations trigger undefined behavior in several edge cases: shifting by negative amounts, shifting by >= bit width of type (e.g., shifting a 64-bit value by 64 bits), or left-shifting negative signed integers. On x86-64 hardware, shifting by 64 actually shifts by 0 (masks to lower 6 bits), making the value unchanged, but this hardware behavior doesn't make the C/C++ code defined. This creates portability nightmares and potential security vulnerabilities.

**Why it happens:**
The C/C++ standards leave these cases undefined, and different compilers/architectures handle them differently. Developers assume shift operations always work like mathematical bit operations. The mask-based behavior on x86 hides bugs during development.

**How to avoid:**
- Guard ALL shift operations with explicit checks:
  ```typescript
  if (shiftAmount < 0 || shiftAmount >= bitWidth) {
    throw new Error(`Invalid shift: ${shiftAmount} for ${bitWidth}-bit value`);
  }
  ```
- Never shift signed integers - always cast to unsigned first
- Use bit width constants: `if (shift >= 32)` not magic numbers
- Add static analysis / linter rules to catch bare shifts
- Consider helper functions: `safeShiftLeft(value, amount, bitWidth)`

**Warning signs:**
- Different results on different architectures (x86 vs ARM)
- Different results between compiler versions
- Crashes or corruption when shift amount comes from user input
- Unexpected zeros or unchanged values after shifts
- Static analyzers warning about shift operations

**Phase to address:**
Core bit manipulation primitives (Phase 1) - establish safe shift operations before building higher-level APIs

---

### Pitfall 3: Endianness Assumptions Breaking Cross-Platform Compatibility

**What goes wrong:**
Binary data serialized on a little-endian system (x86, ARM) cannot be read on a big-endian system (some embedded processors, network protocols) because multi-byte integers are stored in reversed byte order. Developers test on one architecture and ship, then discover corruption when deployed cross-platform or when interfacing with network protocols.

**Why it happens:**
Most modern development happens on little-endian x86/ARM, so endianness bugs remain hidden. Using raw `memcpy` or struct serialization directly transfers bytes without conversion. Developers assume "binary format" means "platform binary format" rather than "specified byte order."

**How to avoid:**
- NEVER serialize C structures directly using memcpy
- Always specify and document byte order in schema (recommend big-endian/network order for interop)
- Use explicit byte-order conversion on encode/decode:
  ```typescript
  writeBigEndianU32(value) {
    bytes[0] = (value >> 24) & 0xFF;
    bytes[1] = (value >> 16) & 0xFF;
    bytes[2] = (value >> 8) & 0xFF;
    bytes[3] = value & 0xFF;
  }
  ```
- Test on both endiannesses (use QEMU if needed)
- Provide endianness configuration option but make it explicit

**Warning signs:**
- "Works on my machine" but fails in production
- Corrupted integers but correct byte-level data
- Problems only appear when interfacing with network protocols or embedded systems
- Values like 0x01020304 becoming 0x04030201

**Phase to address:**
Binary encoding layer (Phase 2) - after core validation, before schema features

---

### Pitfall 4: Off-by-One Errors in Bit Boundary Calculations

**What goes wrong:**
Buffer overruns, incorrect truncation, or data corruption due to incorrect bit/byte boundary math. Common errors include: using `n-m` instead of `n-m+1` for inclusive ranges, confusing bit indices (0-indexed) with bit counts (1-indexed), using `<=` instead of `<` in boundary checks, and calculating byte requirements as `bits/8` instead of `ceil(bits/8.0)`.

**Why it happens:**
Mixing zero-based and one-based counting, inclusive vs exclusive range conventions, and the fencepost problem (counting posts vs gaps). Intuitive mental math is often wrong by one. Integer division truncates instead of rounds up.

**How to avoid:**
- Adopt consistent conventions: half-open intervals [start, end)
- Use explicit helpers: `bitsToBytes(n) = (n + 7) >> 3` (ceiling division)
- Prefer `for (i = 0; i < length; i++)` over `for (i = 0; i <= length-1; i++)`
- Write boundary cases explicitly in tests:
  - 0 bits, 1 bit, 7 bits, 8 bits (exactly 1 byte)
  - 9 bits (requires 2 bytes), 64 bits, 65 bits
- Use inclusive naming: `startBit` and `bitCount` not `startBit` and `endBit`
- Document whether ranges are inclusive or exclusive

**Warning signs:**
- Buffer overruns or underruns by exactly 1 byte
- Last bit/byte of data missing or corrupted
- Crashes on specific data sizes (7, 8, 9 bits)
- Array index out of bounds by 1

**Phase to address:**
Core bit manipulation primitives (Phase 1) - foundational math must be correct before building on it

---

### Pitfall 5: Timestamp Precision Loss in Epoch Conversions

**What goes wrong:**
Converting timestamps between different resolutions (seconds, milliseconds, microseconds, nanoseconds) causes silent precision loss. Integer division like `ms / 1000` loses fractional seconds. Round-trip fails: 1674567890123ms → 1674567890s → 1674567890000ms (lost 123ms). Floating point timestamps lose precision beyond 2^24 seconds (~194 days from epoch for nanosecond resolution).

**Why it happens:**
Developers use integer division without considering remainder. Storing subsecond precision requires composite types (seconds + fractional part) but simple integer types are easier. Different systems have different timestamp resolutions creating impedance mismatches.

**How to avoid:**
- Store timestamps at a single, documented resolution (recommend milliseconds or microseconds)
- Never use floating point for timestamps
- If converting between resolutions, make it explicit and lossy:
  ```typescript
  toSeconds(ms: number): {seconds: number, remainderMs: number} {
    return {seconds: Math.floor(ms / 1000), remainderMs: ms % 1000};
  }
  ```
- For bit packing, store as offset from epoch in single units (e.g., milliseconds since 2024-01-01)
- Document precision limits in schema
- Provide validators for timestamp ranges

**Warning signs:**
- Times "drift" slightly on round-trip
- Milliseconds always zero after deserialization
- Fractional seconds lost
- Future dates overflow (2038 problem with 32-bit seconds)

**Phase to address:**
Type system / date-time handling (Phase 3) - after basic integers work, add specialized temporal types

---

### Pitfall 6: Schema Evolution Breaking Existing Data

**What goes wrong:**
Adding, removing, or changing field types in a schema makes old serialized data unreadable. Common breaking changes include: removing fields (old data has bytes for removed field), changing field types (INT32 → STRING), reordering fields (changes byte offsets), changing field bit widths (8-bit → 16-bit changes alignment), and renaming fields without aliases.

**Why it happens:**
No versioning strategy from day one. Binary formats are tightly coupled to schema structure. Default compatibility mode (if any) doesn't match actual evolution patterns. Testing only with current schema version.

**How to avoid:**
- Include schema version in every serialized blob (4-8 bytes overhead is worth it)
- Design for backward compatibility from v1:
  - Use field IDs/tags, not positions
  - Reserve field IDs when removing (never reuse)
  - Make all new fields optional with defaults
  - Never change field types - deprecate and add new field
- Test with multi-version data:
  - Can v2 deserializer read v1 data?
  - Can v1 deserializer read v2 data (forward compat)?
- Document compatibility guarantees explicitly
- Consider schema registry pattern for validation

**Warning signs:**
- "Cannot deserialize" errors after deployment
- Data corruption on schema updates
- Need to re-serialize all historical data on changes
- Breaking changes discovered in production

**Phase to address:**
Schema evolution (Phase 4 or later) - after basic serialization works, add versioning before shipping to production

---

### Pitfall 7: Nullable Field Encoding Ambiguity

**What goes wrong:**
No way to distinguish between "field is null" vs "field is missing" vs "field has default value of zero." Attempting to serialize null without declaring field as nullable throws NullPointerException. Asymmetric behavior: null on encode is omitted, but on decode missing field is error not null. Runtime type information loss makes nullable vs non-nullable indistinguishable.

**Why it happens:**
Binary formats default to non-nullable for efficiency. Developers conflate "optional" (may be missing) with "nullable" (may be present but null). Trying to save bits by not encoding null indicator. Language type systems (C#, Kotlin) distinguish nullable at compile time but not at runtime.

**How to avoid:**
- Distinguish "optional" from "nullable" in type system:
  - Optional: field may be omitted (uses 1 bit presence flag)
  - Nullable: field always present, value may be null (uses 1 bit null flag)
  - Optional + Nullable: 2 bits (present flag + null flag if present)
- Make fields non-nullable by default, explicit opt-in for nullable
- Use union types for sum types: `null | value` is a union
- Document null handling in schema:
  ```typescript
  field age: uint8?  // nullable, always serialized
  field nickname?: string  // optional, may be omitted
  field metadata?: object?  // optional AND nullable
  ```
- Test null edge cases explicitly

**Warning signs:**
- NullPointerException during serialization
- Confusion between missing field errors and null values
- Asymmetric encode/decode for null values
- Inability to represent "explicitly null" vs "not present"

**Phase to address:**
Type system nullability (Phase 3) - after basic types work, add null/optional semantics

---

### Pitfall 8: Generated Code Being Unreadable and Unmaintainable

**What goes wrong:**
Code generators produce output with: no comments, machine-generated identifiers like `_field_0_offset`, deeply nested expressions that span hundreds of characters, missing type annotations, no whitespace or formatting, and collapsed logic that's impossible to debug. When edge cases fail, developers can't understand or fix the generated code.

**Why it happens:**
Code generation optimizes for machine consumption not human readability. Templates get complex and aren't formatted. Generated code is treated as "build artifact, don't touch." No validation that output is readable.

**How to avoid:**
- Treat generated code as first-class source code
- Format generated output (run prettier/clang-format)
- Add human-readable comments:
  ```typescript
  // Field: age (uint8, bits 0-7)
  const age = (bytes[0] >> 0) & 0xFF;
  ```
- Use meaningful identifiers: `ageFieldOffset` not `_f_2_off`
- Break complex expressions into intermediate variables
- Include schema metadata as comments in generated file
- Generate README alongside code explaining structure
- Test generated code readability (manual review)
- Provide "debug mode" generation with extra comments

**Warning signs:**
- Developers avoid reading generated code
- Edge case bugs require regenerating not fixing
- Stack traces in generated code are incomprehensible
- Can't debug issues without "debug mode" generation

**Phase to address:**
Code generation (Phase 5 or later) - polish before users depend on it

---

### Pitfall 9: Validation Only at Decode Time, Not Encode Time

**What goes wrong:**
Invalid data is encoded successfully but fails on decode, potentially far away in time/space from where it was created. Errors discovered in production when data is read, not when data is written. Root cause is difficult to trace because invalid data was accepted hours/days earlier.

**Why it happens:**
Validation is expensive and developers skip it during encoding for performance. Decode is natural place for validation (parsing untrusted input). Testing only round-trip with valid data doesn't catch encode-time validation gaps.

**How to avoid:**
- Validate at BOTH encode and decode, but with different purposes:
  - Encode-time: "Is this value legal for this schema?" (developer error)
  - Decode-time: "Is this binary data well-formed?" (data corruption or attack)
- Make encode validation strict by default (fail fast)
- Provide "unsafe" encode variant for trusted data with clear naming
- Test encode validation explicitly:
  ```typescript
  expect(() => encode({age: 256})).toThrow("age exceeds 8-bit max");
  expect(() => encode({age: -1})).toThrow("age must be non-negative");
  ```
- Include validation context in errors: field name, schema path, actual value

**Warning signs:**
- Errors discovered long after data creation
- "How did this invalid data get here?"
- Different validation between encode and decode paths
- Production data corruption from bugs in user code

**Phase to address:**
Core validation layer (Phase 1) - establish validation boundaries immediately

---

### Pitfall 10: Alignment and Padding Bytes Breaking Cross-Platform Portability

**What goes wrong:**
Structs serialized with compiler-added padding bytes cannot be deserialized on different platforms with different alignment rules. For example, a struct with `{uint8, uint32}` becomes 8 bytes on one platform (1 byte + 3 padding + 4 bytes) but 5 bytes on another. Loading 32-bit data with 64-bit code corrupts values. Hidden padding bytes may contain uninitialized memory (security issue).

**Why it happens:**
Using raw struct serialization instead of explicit field-by-field encoding. Relying on `sizeof(struct)` which includes padding. Different compilers have different padding rules. `#pragma pack` is non-portable and can break ABI.

**How to avoid:**
- NEVER serialize structs directly - always encode field-by-field
- Use explicit bit/byte layout in schema, not compiler layout
- Use fixed-width types: `uint32_t` not `int` or `size_t`
- Calculate buffer size from schema, not `sizeof`
- Test cross-platform: serialize on 32-bit, deserialize on 64-bit
- If using packed structs, document it's platform-specific
- Zero-initialize all buffers to avoid leaking padding bytes

**Warning signs:**
- Different serialized sizes on different platforms
- Garbage values in deserialized data
- Security scanners finding uninitialized memory in output
- Corruption when moving data between 32-bit and 64-bit systems

**Phase to address:**
Binary encoding layer (Phase 2) - architecture must be platform-independent from the start

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip encode-time validation | Faster encoding | Silent corruption, hard-to-debug production issues | Never - validation is core to correctness |
| Use floating point for timestamps | Simpler API | Precision loss, off-by-one errors at scale | Never - timestamps are discrete |
| Omit schema versioning | Cleaner format | Cannot evolve schema without breaking changes | Early prototyping only, before any persistence |
| Generate minified code | Smaller output | Unmaintainable, impossible to debug | Only if also generating readable "debug" version |
| Allow implicit nullable | Fewer type annotations | Ambiguity between null/missing/zero | Never - be explicit about nullability |
| Hard-code endianness | Skip configuration | Locks to single platform | Single-platform embedded systems only |
| Use language integers (int, long) | Familiar types | Platform-dependent sizes (int is 32-bit or 64-bit) | Never for serialization - use uint32_t |
| Serialize structs with memcpy | Fastest serialization | Non-portable, includes padding, breaks on schema changes | Never - always serialize fields explicitly |
| Wrap overflow instead of error | Performance | Silent data corruption | Only if explicitly opt-in "wrapping mode" |
| Test only round-trip with valid data | Passes all tests | Missing edge cases, encode validation gaps | Never - test encode/decode independently |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Network protocols (TCP/UDP) | Assuming same endianness as host | Always use network byte order (big-endian), convert explicitly |
| Database BLOBs | Assuming schema matches between app versions | Include schema version in blob, validate on read |
| File persistence | Assuming same architecture will read the file | Use portable format with explicit endianness, test cross-platform |
| Message queues | Assuming consumer and producer versions match | Support multiple schema versions, test backward/forward compatibility |
| RPC/gRPC | Sending raw structs over wire | Use IDL (Protocol Buffers, etc.) with versioning support |
| Embedded systems | Assuming same word size (32-bit vs 64-bit) | Use fixed-width types, test on both architectures |
| Language interop (C++ ↔ Python) | Assuming struct layout matches | Define explicit binary format, serialize field-by-field |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Validating every nested object on decode | Decode time increases linearly with nesting depth | Validate at trust boundaries only, skip validation for internal round-trips | Deeply nested schemas (>5 levels) with arrays |
| Recomputing bit offsets on every field access | Slow encoding/decoding | Precompute offsets at schema compilation, cache in generated code | Schemas with >20 fields |
| Using 8-bit types everywhere | Extra masking, widening on some platforms | Use natural word size (32-bit/64-bit) for computation, pack only for storage | Tight loops processing thousands of values |
| Allocating buffer per field | Memory allocation overhead | Allocate once for entire message, reuse buffers | High-frequency encoding (>10k msgs/sec) |
| Dynamic schema lookup on every encode/decode | Hash table lookups add latency | Compile schema to code, use static dispatch | Real-time systems, hot paths |
| Encoding timestamps as strings | Parsing overhead (10-100x slower than binary) | Use binary epoch time (milliseconds since epoch as uint64) | High-volume logging, time-series data |
| Using arbitrary-precision math for bit operations | Slow on all platforms | Use platform integers (uint32/uint64), validate ranges | Hot encoding paths |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Deserializing untrusted data without size limits | Buffer overflow, DoS via memory exhaustion | Set max message size, max array lengths, max nesting depth before deserializing |
| Using deserialized integers as array indices | Out-of-bounds access, memory corruption | Validate all integers against expected ranges BEFORE using as indices |
| Including uninitialized padding bytes | Information disclosure (leaking stack/heap memory) | Zero-initialize all buffers before encoding: `memset(buf, 0, size)` |
| Allowing arbitrary schema in deserialization | Type confusion attacks, RCE | Whitelist allowed schemas, include schema hash in message |
| Trusting length fields from untrusted input | Buffer overrun if length > actual data | Validate length <= remaining_bytes before reading |
| Using bit shifts with untrusted shift amounts | Undefined behavior, potential exploits | Validate shift amount < bit width before shifting |
| Exposing raw binary format over network | Harder to firewall/inspect than text protocols | Add framing layer with magic bytes, version, length header |
| Assuming deserialized data is valid | Exploiting application logic with crafted data | Always validate constraints after deserialization, even if validated at encode time |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Generic error messages: "Validation failed" | Developer spends hours debugging which field/constraint failed | Include field name, value, and constraint: "Field 'age' value 256 exceeds maximum 255 for uint8" |
| Failing silently on overflow | Silent data corruption, users report "wrong data" | Throw clear error: "Cannot pack value 300 into 8-bit field - use uint16 or validate input" |
| Requiring bit-level knowledge for schema definition | High barrier to entry, errors in bit math | Provide high-level API: `uint8`, `uint16` not "8 bits at offset 0" |
| No schema introspection | Can't build generic tools (viewers, validators) | Provide schema metadata API: field names, types, ranges |
| Generated code with no documentation | Developers don't know how to use it | Generate usage examples and field documentation in comments |
| Breaking changes without migration guide | Users stuck on old version or forced to rewrite | Provide migration path: "In v2, field X renamed to Y - update schema with alias" |
| Unclear backward compatibility guarantees | Fear of upgrading, accumulating technical debt | Clearly document: "v1.x can read all v1.y data where y >= x" |
| Magic number bit budgets | Can't understand why schema fails: "Message too large" | Show calculation: "Schema uses 73 bits (65 bits fields + 8 bits metadata), exceeds 64-bit budget" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Encoding works:** Often missing **decode validation** — verify decode rejects malformed input
- [ ] **Round-trip tests pass:** Often missing **edge case testing** — verify min/max values, overflow, underflow
- [ ] **Schema defined:** Often missing **versioning strategy** — verify includes version field and migration plan
- [ ] **Types checked at compile time:** Often missing **runtime validation** — verify runtime checks for values from external sources
- [ ] **Works on developer machine:** Often missing **cross-platform testing** — verify on different endianness, word sizes
- [ ] **Integer encoding works:** Often missing **overflow detection** — verify throws on values exceeding bit width
- [ ] **Timestamps encode:** Often missing **precision documentation** — verify documents resolution and range limits
- [ ] **Nullable fields supported:** Often missing **null vs missing distinction** — verify can represent "explicitly null"
- [ ] **Code generator works:** Often missing **readability check** — verify generated code is debuggable by humans
- [ ] **Fast encoding:** Often missing **encode-time validation** — verify validates before writing, not after
- [ ] **Error thrown on failure:** Often missing **error context** — verify error includes field name, value, constraint
- [ ] **Basic types work:** Often missing **endianness handling** — verify multi-byte integers specify byte order

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent truncation shipped to production | HIGH | 1. Add validation to prevent new corruption 2. Identify corrupted records via heuristics 3. Restore from backups or ask users to re-enter data 4. Add monitoring for value anomalies |
| Endianness mismatch between systems | MEDIUM | 1. Detect endianness at runtime 2. Add conversion layer 3. Re-serialize all stored data 4. May need to keep both formats during transition |
| Schema evolved, old data unreadable | HIGH | 1. If no version field, use heuristics to detect version 2. Write migration code for each version pair 3. Re-serialize to latest version 4. Future: Always include version field |
| Off-by-one causing buffer overruns | LOW | 1. Fix boundary calculation 2. Add tests for edge cases 3. Code review all similar calculations 4. Crashes are detectable, fix is usually simple |
| Generated code has bug in edge case | MEDIUM | 1. Fix template 2. Regenerate all code 3. Deploy update 4. If customers have generated code, provide patch |
| Timestamp precision lost | MEDIUM | 1. Cannot recover lost precision 2. Migrate to higher-resolution format 3. Future data uses new format 4. Document precision loss for old data |
| Nullable field ambiguity | MEDIUM | 1. Define semantics for existing data 2. Add explicit null indicator to schema 3. Migrate data with assumed semantics 4. Update encoders/decoders |
| Bit shift undefined behavior | HIGH | 1. Undefined behavior may have caused anything 2. Validate all affected data 3. Identify patterns of corruption 4. Add shift guards, redeploy, monitor for anomalies |
| Validation only at decode time | MEDIUM | 1. Add encode-time validation 2. Identify source of invalid data 3. Fix root cause 4. Clean up corrupted data |
| Alignment issues cross-platform | MEDIUM | 1. Define explicit, portable format 2. Write field-by-field encoder/decoder 3. Migrate all data 4. Cannot use old format |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent integer truncation/overflow | Phase 1: Core Validation | Test encode throws on overflow for all integer types |
| Bit shift undefined behavior | Phase 1: Bit Manipulation Primitives | Test all shift operations with negative, zero, max, max+1 amounts |
| Off-by-one errors | Phase 1: Bit Boundary Math | Test with 0, 1, 7, 8, 9, 63, 64, 65 bits |
| Validation timing (encode vs decode) | Phase 1: Core Validation | Test encode validation rejects invalid data, decode validation catches corruption |
| Endianness assumptions | Phase 2: Binary Encoding Layer | Cross-platform tests: serialize on little-endian, deserialize on big-endian (QEMU) |
| Alignment and padding | Phase 2: Binary Encoding Layer | Test serialized size matches schema size exactly, no extra bytes |
| Timestamp precision loss | Phase 3: Date-Time Types | Round-trip test with millisecond precision, test overflow for year 2038+ |
| Nullable field ambiguity | Phase 3: Nullability Semantics | Test can distinguish null, missing, and zero values |
| Schema evolution breaking data | Phase 4: Versioning Strategy | Multi-version compatibility tests: v2 reads v1 data, v1 reads v2 data |
| Generated code unreadable | Phase 5: Code Generation Polish | Manual code review, complexity metrics (line length, nesting depth) |

---

## Sources

**Bit-packing and serialization patterns:**
- [GitHub: bitpacker - Type-safe bit level serialization](https://github.com/CrustyAuklet/bitpacker)
- [GitHub: mas-bandwidth/serialize - Bitpacking serializer for C++](https://github.com/mas-bandwidth/serialize)
- [Data Compression: Bit-Packing 101 - KinematicSoup](https://kinematicsoup.com/news/2016/9/6/data-compression-bit-packing-101)
- [Serialization for Embedded Systems - mbedded.ninja](https://blog.mbedded.ninja/programming/serialization-formats/serialization-for-embedded-systems/)

**Integer overflow and underflow:**
- [Integer overflow - Wikipedia](https://en.wikipedia.org/wiki/Integer_overflow)
- [Arithmetic Overflow and Underflow - Vladris Blog](https://vladris.com/blog/2018/10/13/arithmetic-overflow-and-underflow.html)
- [CWE-190: Integer Overflow or Wraparound](https://cwe.mitre.org/data/definitions/190.html)
- [Integer Overflow and Underflow - AussieAI](https://www.aussieai.com/book/ch8-integer-underflow-overflow)

**Bit shift undefined behavior:**
- [INT34-C: Do not shift by negative or >= bits - SEI CERT](https://wiki.sei.cmu.edu/confluence/display/c/INT34-C.+Do+not+shift+an+expression+by+a+negative+number+of+bits+or+by+greater+than+or+equal+to+the+number+of+bits+that+exist+in+the+operand)
- [V610: Undefined behavior - Check the shift operator - PVS-Studio](https://pvs-studio.com/en/docs/warnings/v610/)
- [Knowing Your Hardware ALU Shifter - 64-bit Bit Masks](https://wangziqi2013.github.io/article/2020/07/30/tricky-code-for-64-bit-mask.html)

**Endianness and cross-platform:**
- [Endianness in Modern Computing - Support Tools](https://support.tools/endianness-deep-dive/)
- [GitHub: bitsery - Binary serialization library](https://github.com/fraillt/bitsery)
- [GitHub: bytepack - Configurable endianness, cross-platform](https://github.com/farukeryilmaz/bytepack)
- [When Does Endianness Become a Factor? - codestudy.net](https://www.codestudy.net/blog/when-does-endianness-become-a-factor/)

**Schema evolution and compatibility:**
- [Backward Compatibility in Schema Evolution - DataExpert](https://www.dataexpert.io/blog/backward-compatibility-schema-evolution-guide)
- [Schema Evolution and Compatibility - Confluent](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [Handling Schema Evolution in Kafka Connect - Medium](https://medium.com/cloudnativepub/handling-schema-evolution-in-kafka-connect-patterns-pitfalls-and-practices-391795d7d8b0)
- [Avro Schema Evolution Demystified - Medium](https://laso-coder.medium.com/avro-schema-evolution-demystified-backward-and-forward-compatibility-explained-561beeaadc6b)

**Timestamp serialization:**
- [How to Serialize and Deserialize Dates in Avro - Baeldung](https://www.baeldung.com/avro-serialize-deserialize-dates)
- [Unix time - Wikipedia](https://en.wikipedia.org/wiki/Unix_time)
- [PEP 410: Use decimal.Decimal for timestamps - Python](https://peps.python.org/pep-0410/)

**Null handling:**
- [Storing Null Values in Avro Files - Baeldung](https://www.baeldung.com/avro-storing-null-values-files)
- [kotlinx.serialization: nullable, optional properties - Livefront](https://livefront.com/writing/kotlinx-serialization-de-serializing-jsons-nullable-optional-properties/)
- [C# 8.0 nullable references and serialization - endjin](https://endjin.com/blog/2020/09/dotnet-csharp-8-nullable-references-serialization)

**Off-by-one errors:**
- [Off-by-one error - Wikipedia](https://en.wikipedia.org/wiki/Off-by-one_error)
- [Off-by-One Error - Baeldung CS](https://www.baeldung.com/cs/off-by-one-error)
- [CWE-193: Off-by-one Error](https://cwe.mitre.org/data/definitions/193.html)

**Alignment and padding:**
- [Cross-Language Binary Data Transfer - Medium](https://medium.com/@teamcode20233/cross-language-binary-data-transfer-with-c-and-python-a66003929c3)
- [How I Pack Structs in C - TheLinuxCode](https://thelinuxcode.com/how-i-pack-structs-in-c-without-getting-burned-by-alignment-abi-and-performance/)
- [Ultimate Guide to C Structure Memory Alignment - Markaicode](https://markaicode.com/ultimate-guide-to-c-structure-memory-alignment-and-padding/)

**Validation and code generation:**
- [Encoding and Decoding Custom Objects in Python JSON - TheLinuxCode](https://thelinuxcode.com/encoding-and-decoding-custom-objects-in-python-json-patterns-pitfalls-and-production-practices/)
- [How to Pretty Print JSON - TheLinuxCode](https://thelinuxcode.com/how-to-pretty-print-a-json-string-in-javascript-with-real-world-edge-cases/)

---
*Pitfalls research for: Bit-packing and serialization libraries*
*Researched: 2026-02-19*
