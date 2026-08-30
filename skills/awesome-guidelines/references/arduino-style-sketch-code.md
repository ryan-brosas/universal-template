<!-- capsule-v2 -->
# Sketch code — does setup/loop and C++ layout follow Arduino sketch conventions?

**Source:** Creating library guide (sketch usage) + MakerGuides Arduino C++ style (secondary). **Question:** Are includes, globals, setup/loop lifecycle, naming, and control-flow braces consistent?

## Sketch lifecycle seam
**Path/Symbol:** `*.ino` sketch using library or standalone firmware.
**Signature:** `#include <Lib.h>`; global instance; `setup()` → `begin()`; `loop()` behavior.
**Data Shape:** minimal globals; hardware init only in `setup()` or library `begin()`.

### Decisive pattern
```arduino
#include <Morse.h>

Morse morse(13);

void setup() {
  morse.begin();
}

void loop() {
  morse.dot();
  delay(3000);
}
```

**Flow:** include library with angle brackets when installed → construct library instance at global scope if needed → call `begin()` (and bus setup helpers) from `setup()`, not scattered in `loop()` → keep `loop()` focused on recurring behavior → remove unused `#include` lines to save flash → prefer one instance per resource; use distinct instance names (`morse`, `morse2`) when multiple pins/devices.
**Invariant:** hardware init only in `loop()` without guard, or missing `begin()` after ctor, fails sketch lifecycle review.
**Probe:** trace pinMode/bus calls — must run once from `setup()`/`begin()` path.

## Naming and layout seam
**Flow:** camelCase for variables and functions (`sensorReading`, `readSensor`) → lowercase file names with underscores if splitting `.ino` into tabs/files → 4-space indentation → limit lines to ~80–120 characters → declare variables near first use when reasonable → use descriptive names (not `x`, `temp` alone for domain values).
**Invariant:** snake_case function names in sketch code diverges from Arduino/Processing camelCase norm.
**Probe:** spot-check identifiers; indent width scan.

## Control flow seam
**Flow:** always brace `if`/`else`/`for`/`while` bodies — even single statements → prefer early clarity over nested ternary → comment non-obvious hardware timing or units → on AVR, avoid heavy allocation/String churn in hot `loop()` paths.
**Invariant:** unbraced single-line `if` under maintenance review fails readability/safety check.
**Probe:** grep for `if (` lines without following `{` on same or next line.

## Memory seam
**Flow:** use `const` for pins and fixed config → prefer stack locals in functions over unnecessary globals → mind RAM/flash on 8-bit targets — reuse buffers in libraries inheriting `Stream`.
**Invariant:** unbounded `String` concatenation in tight `loop()` on AVR is a reliability risk.
**Probe:** review `loop()` for `String` growth or `malloc` patterns.

## Verdict
setup/begin/loop discipline, camelCase, 4-space braces, lean globals, AVR-aware loop body. Learning note: `arduino-style-learning-note.md`.
