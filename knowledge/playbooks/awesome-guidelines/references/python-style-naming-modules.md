<!-- capsule-v2 -->
# Naming and modules — is the public API obvious from names and paths?

**Source:** PEP 8 §Naming; Google pyguide §3.16. **Question:** Can a reader tell public vs internal symbols and import the right module?

## Naming seam
**Path/Symbol:** modules, classes, functions, constants.
**Signature:** `lower_with_under.py` files; `CapWords` classes; `CAPS_WITH_UNDER` constants.
**Data Shape:** leading `_` = internal/protected; `ThingError` exceptions.

### Decisive table
```text
module.py          → public module
_helper.py         → internal module (by convention _ prefix)
MyService            → class
connect_to_database() → function
MAX_RETRIES          → constant
ConnectionError      → exception (Error suffix)
```

**Flow:** pick name for scope visibility → use `_` for non-public → avoid abbreviations and type suffixes (`user_dict`) → `.py` extension, no dashes in filenames.
**Invariant:** public names reflect **usage**, not implementation; single-letter names only in tight loops/`except e`/`with f`.
**Probe:** pylint/ruff naming rules; no `HttpServerError` when acronym is HTTP → `HTTPServerError`.

## Module layout seam
**Flow:** related classes/functions live in one module (not Java one-class-per-file) → full package import paths in new code.
**Invariant:** executable scripts still expose importable modules — side effects belong in `main()`, not import time.
**Probe:** `python -c "import pkg.module"` does not open network connections or parse argv.

## Verdict
Adopt PEP 8 + Google naming matrix; `_` marks internal; no dashed module names. Learning note: `python-style-learning-note.md`.
