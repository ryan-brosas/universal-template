<!-- capsule-v2 -->
# Modules and verification — are imports std-shaped and names enforced in CI?

**Source:** NEP-1 §Miscellaneous; Nim Compiler `--styleCheck`. **Question:** Does the build catch spelling drift and stdlib import shape?

## Import seam
**Path/Symbol:** module headers and compile/test commands.
**Signature:** `import std/...`; `--styleCheck:error`; project tests.
**Data Shape:** `nim.cfg` or compile flags with styleCheck.

### Decisive pattern
```nim
import std/[os, strutils, options]

let greeting = """
hello
world
"""

when isMainModule:
  echo parseUrl("https://example.com").hostname
```

```bash
nim c --styleCheck:error --styleCheck:usages src/mypkg.nim
nim test
```

**Flow:** import stdlib with `std/` prefix — single module `import std/os`, multiple `import std/[os, sysrand]` → multiline triple-quoted strings begin content on new line after opener when clearly multiline → compile with `--styleCheck:hint` or `--styleCheck:error` to enforce NEP-1 identifier shapes → add `--styleCheck:usages` when project wants declared spelling consistency without re-declaring all names to NEP-1 → run project test harness (`nim test`, testament, etc.) on changed modules.
**Invariant:** bare `import os` for stdlib, inconsistent identifier spellings, or missing styleCheck in CI for NEP-1-aligned projects fails review.
**Probe:** compile with `--styleCheck:error`; CI flag audit; import prefix grep.

## Export seam
**Flow:** mark stable API with `*` export; keep internal helpers unexported; document public procs/types in module doc comment.
**Invariant:** undocumented exported proc without module doc context fails API review.
**Probe:** export star grep; doc comment coverage on `*`.

## Verdict
std/ imports, styleCheck-enforced names, tests on changed modules. Learning note: `nim-style-learning-note.md`.
