# Pascal style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `pascal-style-*.md` capsules, `pascal-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Free Pascal wiki — Coding style](https://wiki.freepascal.org/Coding_style) (primary) | lowercase keywords; 2-space indent; no tabs; no spaces around operators (FPC compiler); `begin` on own line; `result` return; routine sections indented (FCL exception: top-level routines not indented); `{ }` lowercase comments; two blank lines between subroutines |
| [GNU Pascal Coding Standards](https://www.gnu-pascal.de/h-gpcs-en.html) (secondary) | `.pas` lowercase files; brace comments only; English docs; file header order; const→type→var→label→routines; T/P pointer types; spaces before `(` in calls; 2-space indent; global routines not indented; `-Wall` clean; avoid goto/Exit; `{$if False}` to disable code |

**Routing:** Lazarus/LCL and Delphi VCL code → `delphi-coding-practices`. This slice covers **FPC compiler/GPC** Pascal baselines.

## Mental model

Classic Pascal style splits **FPC compiler density** vs **GNU GPC readability**:

1. **Layout** — 2 spaces; no tabs; `begin`/`end` on own lines; blank lines between units/blocks (GPC) or double between subroutines (FPC).
2. **Naming** — lowercase keywords; PascalCase identifiers (`WriteLn`, `BlockRead`); `T`/`P` type pairs; enum/const group prefixes allowed (`fb_Foo`).
3. **Units** — one program/unit per `.pas`; lowercase filename; license header; interface implementation order mirrors declarations.
4. **Comments/control** — `{ single-space braces }`; no `//` or `(* *)` in published code; `result` (FPC) vs named function result (GPC `function Foo = Bar`); `-Wall`/fpsonar in CI.

## Decision tables

### Layout

| Topic | FPC compiler | GNU GPC (published) |
|---|---|---|
| Indent | 2 spaces | 2 spaces |
| Tabs | forbidden | forbidden |
| Operators | tight `p:=p+i` | space before `(` in calls `Inc (x)` |
| begin | own line, indented | own line |
| else if | `else` not extra-indented | same |
| Line length | project default | ~68–78 cols guidance |
| Between routines | two blank lines | empty line between subroutines/blocks |
| FCL routines | not indented | global routines not indented |

### Naming

| Entity | Rule |
|---|---|
| Keywords/directives | lowercase |
| Identifiers | PascalCase words; no underscores (except enum/const groups) |
| Short locals | lowercase (`i`, `s1`) local only |
| Types | `TMyInt`; pointer `PMyInt = ^TMyInt` declared first |
| Acronyms | language-dependent (`GPC`, `WriteLn`, `EOF`) |
| Macros/conditionals | ALL_CAPS_WITH_UNDERSCORES if unavoidable |

### Units & structure

| Case | Rule |
|---|---|
| Files | one unit/program per `.pas`; lowercase filename |
| Header | description, copyright, license (GPC) |
| Block order | const → type → var → label → routines |
| Object sections | public/protected/private: fields, ctors, dtor, methods |
| Implementation | bodies in interface declaration order |
| Uses | avoid unit cycles; implementation uses when possible |

### Comments & control

| Case | Rule |
|---|---|
| Comments | `{ spaced braces }`; English; before code at same indent |
| Disabled code | `{$if False}…{$endif}` not comment blocks |
| Return | FPC: `result:=`; GPC: named result `function Foo = Bar: Integer` |
| Flow | avoid goto/Exit/Break/Continue when reasonable |
| Loops | never mutate `for` counter or rely on after-loop value |
| Verify | compile `-Wall`; fpsonar house rules optional |

## Anti-patterns

- Tab characters
- UPPERCASE keywords (`BEGIN`)
- `if x then begin` same line (FPC/GPC)
- Spaces around operators in FPC compiler tree
- Missing spaces before `(` in GNU GPC published code
- `(* *)` or `//` comments in published GPC code
- `@synthesize`-style — N/A; `@synthesize` Delphi — use properties
- Function name assignment instead of `result` (FPC)
- Implicit `Result` variable (GPC discourages)
- Empty unit initializer `begin end.`
- Trailing `;` before `end` in case (except last branch before else)
- Undocumented interface declarations (GPC)
- Macros for constants
- goto for ordinary flow
- Multiple units per file
- Mixed FPC-tight and GPC-spaced styles in one project

## Skill trace

| Artifact | Role |
|---|---|
| `pascal-style-formatting-layout.md` | indent, begin/end, spacing variants |
| `pascal-style-naming-types.md` | keywords, PascalCase, T/P |
| `pascal-style-units-structure.md` | files, block order, implementation |
| `pascal-style-comments-control.md` | comments, directives, flow, CI |
| `pascal-coding-practices/SKILL.md` | fpc -Wall / fpsonar in CI |
