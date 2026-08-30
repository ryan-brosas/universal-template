---
name: python-coding-practices
description: "Use when authoring or reviewing Python — PEP 8 layout, Google import and exception rules, naming matrix, mutable-default traps, type-annotated public APIs, and import-safe main guards."
disable-model-invocation: true
---

# Python Coding Practices

Application skill for Python style learning (from the archived `awesome-guidelines` style capsules). For framework-specific patterns, load the stack foundation.

## Core Principle

Python readability is **enforced consistency plus semantic footgun avoidance** — format mechanically, import modules explicitly, never mutable defaults, validate with exceptions not assert.

## When to Use / NOT

- Writing or reviewing Python modules, scripts, or library public APIs.
- Setting up Ruff/Black/mypy gates for a Python repo.

**NOT when:**

- Stack-specific rules dominate (Django ORM, Pydantic models, etc.) — load `*-foundation`.
- Non-Python code.

## Workflow

1. **Format** — 4 spaces, grouped imports, project line length (`python-style-layout-imports.md`).
2. **Name** — public vs `_` internal; `CapWords` classes; `.py` filenames (`python-style-naming-modules.md`).
3. **Errors** — narrow `raise`/`except`; debug-only `assert`; idiomatic `is None`/empty seq (`python-style-exceptions-truthiness.md`).
4. **API surface** — no mutable defaults; type public functions; `main()` guard (`python-style-defaults-types-main.md`).
5. **Verify** — ruff/black + typecheck on changed paths.

## Red Flags

- `def f(items=[]):`
- Bare `except:` or silent `except Exception:`
- `assert` for user input validation
- Side effects at import time
- `from module import MyClass` in application code (Google rule)

## Verification

- `ruff check`, formatter check, `mypy`/`pyright` on public package (project commands).
- Import module without env/network side effects.
- Capsule checklist on review.

## Skill Result Contract

```xml
<skill_result>
  <skill>python-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>py diff, ruff/mypy output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>mutable default, broad except, missing types, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/python-style-learning-note.md`
- `awesome-guidelines/references/python-style-layout-imports.md`
- `awesome-guidelines/references/python-style-naming-modules.md`
- `awesome-guidelines/references/python-style-exceptions-truthiness.md`
- `awesome-guidelines/references/python-style-defaults-types-main.md`
