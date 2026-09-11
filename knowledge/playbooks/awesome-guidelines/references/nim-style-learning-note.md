# Nim style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `nim-style-*.md` capsules, `nim-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [NEP-1 Standard Library Style Guide](https://nim-lang.org/docs/nep1.html) (primary) | 2-space indent; 80 cols; PascalCase types; camelCase identifiers; abbrev vocabulary; init/new; result over return; proc over macro; let immutability; multiline indent; std/ imports; Error/Defect suffixes |
| [Nim Compiler User Guide — styleCheck](https://nim-lang.org/docs/nimc.html) (secondary) | `--styleCheck:hint|error` enforces NEP-1 names; `--styleCheck:usages` enforces declared spellings only |

**Not duplicated here:** Nim 2 style-insensitivity RFC debate — use project `--styleCheck:usages` when legacy spellings differ. Full stdlib abbrev table lives in NEP-1; capsules cite high-signal rows.

## Mental model

NEP-1 optimizes for **guessable stdlib-shaped APIs**:

1. **Layout** — 2 spaces; 80 columns; no tabstops; avoid manual column alignment.
2. **Naming** — PascalCase types; camelCase procs/vars; real-word acronyms (`parseUrl`); subjectVerb (`fileExists`).
3. **Types** — Obj/Ref/Ptr suffixes; Error/Defect exceptions; enum prefixes unless `{.pure.}`.
4. **Procedures** — assign `result`; `return` only for control flow; `let` default; `proc` before macro/template.
5. **Modules & verify** — `import std/[os, strutils]`; triple-quote newline; `a..b` ranges; `--styleCheck` + tests in CI.

## Decision tables

### Layout

| Topic | Rule |
|---|---|
| Indent | 2 spaces; tabs forbidden (compiler enforced) |
| Line length | ≤ 80 characters |
| Alignment | avoid manual column alignment of types/fields |
| Multiline | indent params; double-indent sig vs body when helpful |
| Ranges | `a..b`, `a..<b`; space only when RHS has operator |
| Literals | multiline `"""` start on new line after opener |

### Naming

| Entity | Convention |
|---|---|
| Types | PascalCase |
| Vars/procs | camelCase (vars start lowercase) |
| Constants | camelCase or PascalCase; avoid ALL_CAPS except C wrappers |
| Acronyms | treat as words (`parseUrl`, not `parseURL`) |
| Mutating views | `m` prefix (`mitems`, `mpairs`) |
| In-place vs copy | `reverse` / `reversed`; `-In` suffix for in-place variant |
| init/new | `initFoo` value; `newFoo` ref |
| Errors | `*Error` / `*Defect` suffix |
| Enums | prefixed camelCase unless `{.pure.}` PascalCase members |
| Ref variants | base name for common form; `Ref`/`Ptr`/`Obj` suffix for others |

### Procedures & API

| Case | Rule |
|---|---|
| Return | prefer `result =`; `return` for early exit only |
| Immutability | `let` when not reassigned |
| Power features | `proc` first; macro/template/iterator only when needed |
| Find vs contains | `find` → index; `contains` → bool |
| Getters | field name for O(1 pure access; `getFoo` when side effects/non-O(1) |
| Setters | `foo=` / `setFoo` parallel to getter rules |
| Self | `self` parameter name for method-like procs |

### Modules & verification

| Case | Rule |
|---|---|
| Stdlib import | `import std/os` or `import std/[os, strutils]` |
| Style gate | `nim c --styleCheck:error` (or `hint`) |
| Usages only | add `--styleCheck:usages` for spelling consistency without NEP-1 on declarations |
| Tests | `testament`/project test harness on changed modules |

## Anti-patterns

- Tab indentation
- Lines > 80 without break
- Manual aligned type blocks (re-align churn)
- `parseURL`, `checkHTTPHeader` shouting acronyms
- `existsFile` verbSubject order
- Bare `Exception` subtype (prefer `CatchableError`/`Defect`)
- Unprefixed non-pure enum members
- `var` when value never mutates
- Macro/template where `proc` suffices
- `getLen` instead of `len`
- `append` instead of `add`
- Triple-quote glued to first content line when multiline
- `a .. b` with unnecessary spaces
- Inconsistent identifier spelling across usages (styleCheck)

## Skill trace

| Artifact | Role |
|---|---|
| `nim-style-formatting-layout.md` | indent, 80 cols, multiline breaks |
| `nim-style-naming-types.md` | PascalCase/camelCase, enums, init/new |
| `nim-style-procedures-api.md` | result, let, proc choice, API verbs |
| `nim-style-modules-verify.md` | std imports, literals, styleCheck |
| `nim-coding-practices/SKILL.md` | styleCheck + tests in CI |
