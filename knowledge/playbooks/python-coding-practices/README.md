---
title: python-coding-practices
summary: Use when authoring or reviewing Python, PEP 8 layout, Google import and exception rules, naming matrix, mutable-default traps, type-annotated public APIs, and import-safe main guards.
kind: playbook
---

# Python Coding Practices

Application skill for Python style. For framework-specific patterns, consult the framework's own source or docs.

## Core Principle

Follow the project formatter, import conventions, and error model. Google-style
imports are optional unless adopted; mutable-default sharing and input validation
need behavioral review, not just a style check.

## When to Use / NOT

- Writing or reviewing Python modules, scripts, or library public APIs.
- Setting up Ruff/Black/mypy gates for a Python repo.

**NOT when:**

- Stack-specific rules dominate (Django ORM, Pydantic models, etc.), consult the framework's own source or docs.
- Non-Python code.

## Workflow

1. **Format**, 4 spaces, grouped imports, project line length.
2. **Name**, public vs `_` internal; `CapWords` classes; `.py` filenames.
3. **Errors**, narrow `raise`/`except`; debug-only `assert`; idiomatic `is None`/empty seq.
4. **API surface**, no mutable defaults; type public functions; `main()` guard.
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
