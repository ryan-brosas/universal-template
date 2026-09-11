<!-- capsule-v2 -->
# Exceptions and truthiness — are errors explicit and conditions idiomatic?

**Source:** Google pyguide §2.4, §2.14; PEP 8 §Programming Recommendations. **Question:** Will failures be debuggable and boolean checks correct for `None`?

## Exception seam
**Path/Symbol:** `raise` / `try` / `except` blocks.
**Signature:** built-in exceptions for preconditions; custom `FooError` subclasses.
**Data Shape:** small `try` bodies; `with` for resources.

### Decisive contrast
```python
def connect(minimum: int) -> int:
    if minimum < 1024:
        raise ValueError(f"Min port must be >= 1024, not {minimum}.")
    port = find_port(minimum)
    if port is None:
        raise ConnectionError(f"No port >= {minimum}.")
    assert port >= minimum  # debug invariant only
    return port
```

**Flow:** validate with `if` + `raise` → catch specific exceptions → never swallow with bare `except:` → cleanup via `with`/`finally`.
**Invariant:** `assert` is not API validation — it may be stripped with `-O`; do not use `assert` for control flow users depend on.
**Probe:** no bare `except:`; no `except Exception:` without re-raise comment; try blocks ≤ few lines in review.

## Truthiness seam
```python
if users: ...
if value is None: ...
if not x and x is not None: ...  # distinguish False from None
```

**Flow:** empty seq → falsy; `None` checks use `is`/`is not`; don't compare `== True`; prefer `startswith` over slice compare.
**Invariant:** never `x = x or []` for optional arg default — use `if x is None: x = []`.
**Probe:** grep `== True`, `len\(.*\) == 0`, `type\(.*\) is` flagged in review or lint where configured.

## Verdict
Adopt narrow exceptions, debug-only assert, idiomatic truthiness/`is None`. Learning note: `python-style-learning-note.md`.
