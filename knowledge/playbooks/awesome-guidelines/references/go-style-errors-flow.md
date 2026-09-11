<!-- capsule-v2 -->
# Errors and control flow — are failures explicit and the happy path visible?

**Source:** Google Go decisions §Errors, §Don't panic; Effective Go §Functions; Uber §Don't Panic. **Question:** Can callers handle failures without panics or silent discards?

## Error return seam
**Path/Symbol:** functions that can fail.
**Signature:** `(T, error)` with `error` last; exported APIs return `error` interface.
**Data Shape:** lowercase error strings; `%w` wrapping when adding context.

### Decisive pattern
```go
func Lookup(key string) (string, error) {
    v, ok := store[key]
    if !ok {
        return "", fmt.Errorf("no value for %q", key)
    }
    return v, nil
}

func Process(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return fmt.Errorf("open %q: %w", path, err)
    }
    defer f.Close()
    // ...
    return nil
}
```

**Flow:** return error as extra value → guard with early return → propagate or wrap → never use sentinel `-1`/magic nil as only signal.
**Invariant:** non-error results are **unspecified** when `err != nil`; callers must check error first.
**Probe:** `staticcheck`/review: no ignored errors without comment; no in-band error returns in new APIs.

## Panic & defer seam
**Flow:** production code returns `error` → reserve `panic` for init/`MustCompile`/`MustParse` at startup → tests use `t.Fatal`.
**Invariant:** panic is not a control-flow strategy; `defer` pairs with acquire (files, locks).
**Probe:** grep `panic(` outside `Must*`, test helpers, or main init; defer present on `Open`/lock paths.

## Verdict
Adopt explicit errors, early returns, defer cleanup, no production panic. Learning note: `go-style-learning-note.md`.
