# Arduino platform style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `arduino-style-*.md` capsules, `arduino-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Arduino Style Guide for Creating Libraries](https://github.com/arduino/docs-content/blob/main/content/learn/08.contributions/01.arduino-library-style-guide/arduino-library-style-guide.md) (primary) | Beginner-first API mental model; `read()`/`write()`/`begin()`/`end()`; camelCase; avoid pointers/boolean args; Stream/Print/Client/Server patterns; high-level wrappers |
| [Writing a Library for Arduino](https://github.com/arduino/docs-content/blob/main/content/learn/08.contributions/03.arduino-creating-library-guide/arduino-creating-library-guide.md) (primary) | `.h`/`.cpp`; `#include "Arduino.h"`; include guards; constructor vs `begin()`; `_pin` private prefix; `keywords.txt`; `examples/`; `library.properties` |
| [MakerGuides C++ Style Guide for Arduino](https://www.makerguides.com/cpp-style-guide-for-arduino/) (secondary) | Sketch camelCase; 4-space indent; braces on control flow; declare near use; 80–120 col lines; Doxygen optional |
| SparkFun “So You Want to Make an Arduino Library” (secondary pointer) | Confirms packaging/examples pattern; defer to official docs for API naming |

**Scope:** Arduino **libraries** and **sketches** (AVR/ARM boards, Arduino IDE / arduino-cli). **Generic C++:** `cpp-coding-practices` for non-Arduino trees. **Embedded without Arduino core:** not here.

## Mental model

Arduino quality is **beginner-readable APIs over professional C++ purity**:

1. **Library API** — everyday words, camelCase, `read`/`write`/`begin`/`end`, hide pointers and low-level bus steps behind high-level calls.
2. **Library structure** — `.h` declaration + `.cpp` implementation; guards; hardware init in `begin()` not constructor; private `_member` prefix.
3. **Sketch style** — `setup()`/`loop()`; camelCase; 4-space indent; braces on all blocks; minimal globals.
4. **Packaging/verify** — `keywords.txt`, `examples/`, optional `library.properties`; compile with example sketch via IDE or `arduino-cli`.

## Decision tables

### Library API (official style guide)

| Topic | Rule |
|---|---|
| Audience | intelligent non-programmer; clear mental model first |
| Naming | full everyday words; camelCase functions (`analogRead`, not `analog_read`) |
| I/O verbs | `read()` inputs, `write()` outputs — match core (`digitalRead`, `analogWrite`) |
| Lifecycle | `begin(settings…)` to start; `end()` to stop — not hardware setup in constructor |
| Constants | avoid ALL_CAPS walls when shorter names work |
| Booleans | prefer two named functions over `bool` parameter |
| Pointers | avoid in public API; per-axis getters vs `readAccel(&x,&y,&z)` |
| Streams | accept `Stream&` (not hard-coded `Serial`); byte libraries inherit `Stream` |
| Domain terms | define in plain language before using jargon; avoid “error” for benign events |
| Examples | Adafruit BMP085/DHT/RTClib as high-level abstraction patterns |

### Library files & class layout

| Topic | Rule |
|---|---|
| Files | `Name.h` + `Name.cpp` minimum; true `.h`/`.cpp` extensions |
| Header | `#include "Arduino.h"`; `#ifndef Name_h` guard; class with public API + private state |
| Constructor | store config only — no `pinMode`/bus init |
| `begin()` | hardware configuration called from sketch `setup()` |
| Private fields | leading underscore (`_pin`) matching header |
| Implementation | `#include "Arduino.h"` + `#include "Name.h"`; `Class::method` definitions |
| Comments | file header: name, description, author, date, license |
| IDE highlight | `keywords.txt`: class `KEYWORD1`, methods `KEYWORD2`, tab-separated |
| Examples | `examples/ExampleSketch/ExampleSketch.ino` under library folder |
| Registry | `library.properties` for Library Manager (see arduino-cli library spec) |

### Sketch C++ style (secondary + core patterns)

| Topic | Rule |
|---|---|
| Structure | `#include <Lib.h>`; global instance; `setup()` calls `begin()`; `loop()` drives behavior |
| Variables | camelCase; descriptive; declare close to first use when practical |
| Functions | camelCase; one clear purpose |
| Indent | 4 spaces per level |
| Control flow | braces on `if`/`else`/`for`/`while` even for single statements |
| Line length | ~80–120 characters |
| Memory | prefer `const`/scoped locals; mind RAM on AVR — no heap churn in `loop()` |
| Serial | pass `Stream` into libraries when multi-port or SoftwareSerial |

## Anti-patterns

- Hardware init (`pinMode`, Wire.begin) inside constructor
- `snake_case` public method names on Arduino libraries
- Public API requiring `&` / `*` from sketch authors
- Single `readAll(&a,&b,&c)` when separate `readX()`/`readY()`/`readZ()` reads clearer
- Boolean flag parameters instead of named alternatives
- Hard-coded `Serial` only — breaks Mega alternate ports / SoftwareSerial
- Missing `#include "Arduino.h"` in library header
- Duplicate include without guard
- `.cpp` named `.cpp.txt` or `.ino` inside library source
- Terse ALL_CAPS constant names without readability need
- Exposing raw I2C/register steps as only API when one high-level value is the goal
- Empty `loop()` busy-wait without `yield()` in stream `write()` wait paths (library side)
- Skipping `examples/` or compile check before publish

## Skill trace

| Artifact | Role |
|---|---|
| `arduino-style-library-api.md` | naming, read/write/begin, Stream, beginner API |
| `arduino-style-library-structure.md` | .h/.cpp, guards, begin vs ctor, _prefix |
| `arduino-style-sketch-code.md` | setup/loop, indent, control flow, memory |
| `arduino-style-packaging-verify.md` | keywords, examples, library.properties, compile |
| `arduino-coding-practices/SKILL.md` | library + sketch review workflow |

## Relation to `cpp-coding-practices`

| Arduino-specific | Keep from generic C++ |
|---|---|
| camelCase method names (Processing heritage) | RAII where appropriate outside ctor HW rule |
| `begin()`/`end()` lifecycle | include guards, one-definition rule |
| Hide pointers from beginners | const correctness on interfaces |
| Stream/Print inheritance for IO libs | minimize dynamic allocation in hot paths |
| keywords.txt + examples packaging | comment non-obvious rationale |
