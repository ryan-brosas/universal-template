---
name: python-coding-practices
description: "Use when authoring or reviewing Python, PEP 8 layout, Google import and exception rules, naming matrix, mutable-default traps, type-annotated public APIs, and import-safe main guards."
invocation: manual
disable-model-invocation: true
---

# Python Coding Practices

Application skill for Python style learning (from the archived `awesome-guidelines` style capsules). For framework-specific patterns, load the stack capsules in `skills/*-foundation`.

## Core Principle

Follow the project formatter, import conventions, and error model. Google-style
imports are optional unless adopted; mutable-default sharing and input validation
need behavioral review, not just a style check.

## When to Use / NOT

- Writing or reviewing Python modules, scripts, or library public APIs.
- Setting up Ruff/Black/mypy gates for a Python repo.

**NOT when:**

- Stack-specific rules dominate (Django ORM, Pydantic models, etc.), load `skills/*-foundation`.
- Non-Python code.

## Workflow

1. **Format**, 4 spaces, grouped imports, project line length (`python-style-layout-imports.md`).
2. **Name**, public vs `_` internal; `CapWords` classes; `.py` filenames (`python-style-naming-modules.md`).
3. **Errors**, narrow `raise`/`except`; debug-only `assert`; idiomatic `is None`/empty seq (`python-style-exceptions-truthiness.md`).
4. **API surface**, no mutable defaults; type public functions; `main()` guard (`python-style-defaults-types-main.md`).
5. **Verify**, use configured formatter/lint/typecheck commands on changed paths;
   do not introduce Ruff, Black, or a typechecker merely to run this checklist.

## Red Flags

- `def f(items=[]):`
- Bare `except:` or silent `except Exception:`
- `assert` for user input validation
- Side effects at import time
- A Google-specific import convention applied where the project has not adopted it

## Verification

- `ruff check`, formatter check, `mypy`/`pyright` on public package (project commands).
- Import module without env/network side effects.
- Capsule checklist on review.


## References

- `awesome-guidelines/references/python-style-learning-note.md`
- `awesome-guidelines/references/python-style-layout-imports.md`
- `awesome-guidelines/references/python-style-naming-modules.md`
- `awesome-guidelines/references/python-style-exceptions-truthiness.md`
- `awesome-guidelines/references/python-style-defaults-types-main.md`
