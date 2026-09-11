<!-- capsule-v2 -->
# Documentation and testing — are public symbols documented and tested?

**Source:** D Style §Documentation, §Unit Tests, §Attributes (Phobos). **Question:** Can consumers read Ddoc and trust unittest coverage?

## Ddoc seam
**Path/Symbol:** public functions, types, constants exported from modules.
**Signature:** Ddoc on every public symbol; Params and Returns sections.
**Data Shape:** `/**` or `/++` block comments without per-line stars.

### Decisive pattern
```d
/**
Checks whether a number is positive.
`0` isn't considered a positive number.

Params:
    number = number to be checked

Returns: `true` if the number is positive, `false` otherwise.

See_Also: $(LREF isNegative)
*/
bool isPositive(int number)
{
    return number > 0;
}

/// A public constant exposed in documentation.
enum defaultTimeoutSecs = 30;
```

**Flow:** document all public symbols → Params/Returns on functions → indent continued section text → avoid `///` star columns → use `---` for examples only.
**Invariant:** exported function without Params/Returns or missing public symbol in docs fails review.
**Probe:** `dmd -D` / ddox build; documentation coverage check.

## Unittest and attributes seam
```d
pure nothrow @nogc @safe
bool isEven(int n)
{
    return (n & 1) == 0;
}

unittest
{
    assert(isEven(4));
    assert(!isEven(3));
}
```

**Flow:** place `unittest` immediately after tested function → cover every path; use coverage analyzer → annotate non-template functions with matching `@safe`/`@nogc`/`pure`/`nothrow` alphabetically → no `unittest` inside templates (tests outside).
**Invariant:** template-embedded unittest generating N instances, or missing attributes on always-inferable non-template fn, fails Phobos-style review.
**Probe:** `dub test` / project test runner; `-cov` coverage report on changed modules.

## Verdict
Ddoc Params/Returns, adjacent unittest, explicit attributes, no template tests. Learning note: `d-style-learning-note.md`.
