<!-- capsule-v2 -->
# Packaging and verify — is the library installable with examples and a clean compile?

**Source:** Writing a Library for Arduino + arduino-cli library specification (secondary). **Question:** Are keywords, examples, metadata, and compile checks present before share or Library Manager publish?

## IDE metadata seam
**Path/Symbol:** `keywords.txt` beside `LibraryName.h`.
**Signature:** tab-separated keyword and `KEYWORD1`/`KEYWORD2` kind.
**Data Shape:** class name → KEYWORD1; methods → KEYWORD2.

### Decisive pattern
```text
Morse	KEYWORD1
begin	KEYWORD2
dash	KEYWORD2
dot	KEYWORD2
```

**Flow:** add `keywords.txt` with TAB (not spaces) between name and kind → class names `KEYWORD1`, functions `KEYWORD2` → restart IDE or reload so syntax highlight picks up symbols → optional but recommended for every published library.
**Invariant:** space-separated keywords line fails IDE highlighter parsing.
**Probe:** open keywords.txt; verify tab character between columns.

## Examples seam
**Flow:** create `examples/` under library root → each example in own folder `examples/DescriptiveName/DescriptiveName.ino` → example includes library header and demonstrates primary API path → add comments explaining wiring and expected serial output → example must compile unchanged on target board class.
**Invariant:** library without compilable example fails discoverability and regression anchor.
**Probe:** compile example sketch via IDE or `arduino-cli compile --library path`.

## Registry seam
**Flow:** for Library Manager, add `library.properties` per [arduino-cli library specification](https://arduino.github.io/arduino-cli/latest/library-specification/) → set name, version, author, sentence, paragraph, category, architectures → follow registry FAQ for publish workflow → keep semver-ish version bumps on API changes.
**Invariant:** missing or invalid `library.properties` blocks Library Manager indexing.
**Probe:** `arduino-cli lib list` / validate properties file fields locally.

## Verify seam
**Flow:** after structural changes, compile library with at least one example for each supported architecture → verify `.cpp`/`.h` extensions are real (no `.ino` inside library src) → run serial/example smoke test on hardware or documented simulator when feasible → document board requirements in example header comment.
**Invariant:** library that fails example compile on declared architecture is not release-ready.
**Probe:**
```bash
arduino-cli compile --fqbn arduino:avr:uno examples/Basic/Basic.ino --library .
```
(adapt FQBN and example path to project)

## Verdict
keywords.txt tab format, examples/ compiles, library.properties for publish, arduino-cli compile gate. Learning note: `arduino-style-learning-note.md`.
