---
title: arduino-coding-practices
summary: Use when authoring or reviewing Arduino libraries/sketches, camelCase read/write/begin API,.h/.cpp structure, setup/loop lifecycle, Stream-aware serial, keywords/examples, and arduino-cli compile verify.
kind: playbook
---

# Arduino Coding Practices

Application skill for Arduino library + sketch guides. For portable C++ outside Arduino core, load `cpp-coding-practices`. Professional embedded without Arduino APIs: follow project RTOS/SDK docs.

## Core Principle

Arduino quality is **beginner-first APIs and compile-ready packaging**, camelCase high-level methods, hardware init in `begin()` not constructors, guarded `.h`/`.cpp` pairs, examples that build.

## When to Use / NOT

- Arduino libraries (`*.h`/`*.cpp`), sketch `.ino`, `library.properties`, Library Manager prep.
- Reviewing public API names, Stream serial ports, Morse-style class layout.

**NOT when:**

- Generic C++ desktop/server code, `cpp-coding-practices`.
- Bare-metal non-Arduino SDK firmware with no Arduino core.
- Python MicroPython/CircuitPython, stack-specific docs.

## Workflow

1. **API**, naming, read/write/begin, Stream, no pointer traps.
2. **Structure**, guards, ctor vs begin, `_private` fields.
3. **Sketches**, setup/loop, camelCase, braces, AVR loop discipline.
4. **Packaging**, keywords, examples, properties, compile.
5. **Verify**, `arduino-cli compile` on example; hardware smoke if available.

## Red Flags

- `pinMode` or bus init inside constructor
- snake_case public library methods
- Public API requiring pointer args (`&x`, `char*`) from sketches
- Boolean parameters instead of two named methods
- Hard-coded `Serial` only (no `Stream&`)
- Missing `#include "Arduino.h"` or include guard in library header
- Wrong file extensions (`.cpp.txt`, library `.ino` source)
- Missing `begin()` when hardware setup required
- No `examples/` sketch or example fails compile
- ALL_CAPS constant walls hurting readability
- Heavy `String` allocation in tight `loop()` on AVR
- Unbraced single-line `if` in maintained sketch code
- Publish without `library.properties` when targeting Library Manager

## Verification

- `arduino-cli compile` on primary example with project FQBN
- Header review: guards, `Arduino.h`, public camelCase, private `_fields`
- Constructor vs `begin()` split check
- `keywords.txt` tab-separated spot check
- Optional: compare API to Adafruit high-level wrapper pattern (one call → one user value)


## Related skills

- `cpp-coding-practices`, portable C++ layout and ownership
- `c-coding-practices`, low-level C safety when mixing C drivers
