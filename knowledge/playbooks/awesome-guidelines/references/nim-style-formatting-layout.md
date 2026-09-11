<!-- capsule-v2 -->
# Formatting and layout — is NEP-1 spacing mechanical without alignment churn?

**Source:** NEP-1 §Spacing and Whitespace; §Multi-line statements. **Question:** Will diffs stay small and lines stay scannable at 80 columns?

## Layout seam
**Path/Symbol:** `.nim` sources, especially `src/` and `tests/`.
**Signature:** 2-space indent; ≤80 columns; no tabstops; no manual column alignment.
**Data Shape:** broken multiline sigs/calls with continued indent.

### Decisive pattern
```nim
type
  EventCallback = proc(
    timeReceived: Time, errorCode: int, event: Event,
    output: var string)

proc lotsOfArguments(
    argOne: string, argTwo: int, argThree: float,
    argFour: proc(), argFive: bool, argSix: int
): GenericType[int, string] =
  discard

startProcess(
  nimExecutable, currentDirectory, compilerArguments,
  environment, processOptions)
```

**Flow:** indent blocks with 2 spaces — compiler rejects tabs → keep lines ≤80 characters; wrap instead of horizontal scroll → do not vertically align assignment columns in type blocks (re-align pain on edit) → break long tuple/proc types and proc signatures across lines with continued indent → multiline calls indent args like declarations; double-indent signature vs body when it clarifies nested blocks → prefer current continued-indent style over legacy brace-column alignment in new code.
**Invariant:** tabs, >80-char unbroken lines, or manually aligned type columns fail NEP-1 review.
**Probe:** ruler at 80; `grep $'\t'`; visual alignment audit on `type` blocks.

## Range/literal seam
**Flow:** write `a..b`, `a..<b`, `a..^b` without spaces unless RHS operator needs them (`a .. -3`) → multiline triple-quoted strings start content on newline after `"""` when multiline.
**Invariant:** spaced `a .. b` without operator need, or `"""foo` glued multiline opener fails minor review.
**Probe:** range spacing spot check; string literal first-line review.

## Verdict
Two-space, 80-column, non-aligned wraps, consistent multiline breaks. Learning note: `nim-style-learning-note.md`.
