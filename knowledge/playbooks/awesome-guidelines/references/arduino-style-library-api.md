<!-- capsule-v2 -->
# Library API — does the public surface read like core Arduino to a beginner?

**Source:** Arduino library style guide (API principles). **Question:** Are names, verbs, and lifecycle hooks aligned with core `read`/`write`/`begin` patterns and free of pointer/boolean traps?

## Naming seam
**Path/Symbol:** public methods on library class(es).
**Signature:** camelCase verbs; everyday words; constants readable without ALL_CAPS walls.
**Data Shape:** high-level return values (pressure, temperature) with optional mid-level escape hatches.

### Decisive pattern
```arduino
class AdafruitBMP085 {
  public:
    void begin();
    float readPressure();
    float readTemperature();
    int32_t readRawPressure();  // mid-level, optional
};
```

**Flow:** name functions with full everyday words — not terse abbreviations unless widely known (`SPI`, `HTML`) → use camelCase (`readTemperature`, never `read_temperature`) → organize public methods around what the user thinks the device **does**, not the chip's register map → wrap common multi-step sequences into one high-level call that returns the value in expected units → expose mid-level steps only when advanced users need them → match API shape to real capability (enum-like choices: named methods or constrained types, not arbitrary `int` for small fixed sets) → document domain terms in plain language before using them in names.
**Invariant:** snake_case public methods, cryptic abbreviations, or register-level-only API when a single high-level reading exists fails Arduino library review.
**Probe:** compare method list to core names (`digitalRead`, `analogWrite`, `Wire.begin`); grep public API for `_` in method names.

## Lifecycle seam
**Flow:** constructor stores configuration (pin, address) only → `begin(...)` performs hardware/bus init from sketch `setup()` → optional `end()` stops/deinitializes → do not call `pinMode`, `Wire.begin`, etc. from constructor.
**Invariant:** hardware side effect in constructor fails Arduino lifecycle rule (MCU not ready at global ctor time).
**Probe:** read constructor body — must not touch pins/buses; `begin()` must exist when hardware setup required.

## I/O and Stream seam
**Flow:** use `read()` for inputs and `write()` for outputs where applicable → for serial, accept `Stream&` (reference, not pointer) via ctor or `begin()` — never hard-code only `Serial` → byte-stream libraries inherit `Stream`; buffer reads; `write()` may block but call `yield()` while waiting → for networking, model on `Client`/`Server` when appropriate.
**Invariant:** library that only works on `Serial` and ignores `Stream` fails multi-port and SoftwareSerial use cases.
**Probe:** constructor/`begin()` signature includes `Stream&` or base accepts `Print&`; stream class extends `Stream` if providing byte IO.

## Beginner safety seam
**Flow:** avoid boolean parameters — supply two differently named functions instead → avoid pointer parameters in public API — prefer per-field getters or pass-by-array syntax over `*` → avoid words like "error" for non-fatal conditions → avoid exposing implementation details while keeping mental model accurate.
**Invariant:** public method requiring sketch author to pass `&variable` fails beginner-safe API rule.
**Probe:** grep public headers for `bool` parameters and `*` in method declarations exposed to sketches.

## Verdict
camelCase everyday verbs, `begin()` lifecycle, Stream-aware serial, high-level reads/writes, no pointer/boolean public traps. Learning note: `arduino-style-learning-note.md`.
