# Visual Basic style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `vb-style-*.md` capsules, `vb-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Visual Basic Coding Conventions](https://learn.microsoft.com/en-us/dotnet/visual-basic/programming-guide/program-structure/coding-conventions) (primary) | 4-space indent; one statement/declaration per line; no `:`; implicit line continuation; comment style; string interpolation; arrays `As String()`; Try/Catch not On Error; IsNot; With; Handles; LINQ alignment |
| [Visual Basic Naming Conventions](https://learn.microsoft.com/en-us/dotnet/visual-basic/programming-guide/program-structure/naming-conventions) (primary) | PascalCase words; verb methods; noun classes; `I` interfaces; EventHandler/EventArgs suffixes; avoid shadowing; ≤32 char names when practical |
| [Visual Basic/Coding Standards (Wikibooks)](https://en.wikibooks.org/wiki/Visual_Basic/Coding_Standards) (secondary — legacy) | VB6 Hungarian prefixes (`g`/`m`/`i`/`s` tags); customer standards win on conflict; documents what **not** to port to VB.NET |
| [VB.NET Coding Guidelines (Cory Smith)](http://addressof.com/posts/vb-net-coding-guidelines/) (secondary) | Option Explicit/Strict per file; `m_` private fields; XML docs; one public type per file; Modules for shared-only helpers; no type suffix chars |

**Scope:** Visual Basic .NET (`.vb` on .NET Framework/Core). Legacy VB6/VBA Wikibooks Hungarian notation applies only when maintaining pre-.NET code — new .NET work follows Microsoft + Framework Design Guidelines.

## Mental model

VB.NET quality is **Framework-aligned naming + strict options + readable blocks**:

1. **Formatting** — 4-space spaces-only indent, Pretty Listing, one statement per line, blank lines between members.
2. **Naming/types** — PascalCase public API; camelCase locals/params; optional `m_` private fields; no `My`/`my` in names.
3. **Idioms** — Option Strict/Explicit; Try/Catch/Using; interpolation; modern arrays/events/LINQ patterns from MS docs.
4. **Docs/verify** — XML summaries on public API; one public type per file; `dotnet format`/build/test.

## Decision tables

### Layout & comments

| Topic | Rule |
|---|---|
| Indent | 4 spaces (tabs as spaces); Pretty Listing |
| Statements | one per line; no `:` separator |
| Continuation | implicit over `_` when possible |
| Declarations | one per line; left-align list continuations |
| Spacing | blank line between methods/properties |
| Comments | own line; `' Text.` with space after `'` |
| Block If | full `If`/`End If` (Cory Smith); avoid empty Else |

### Naming

| Entity | Convention |
|---|---|
| Types/properties/methods/events | PascalCase (`FindLastRecord`) |
| Interfaces | `I` + noun (`IComponent`) |
| Methods | verb-first (`CloseDialog`) |
| Classes/structures | noun-first (`EmployeeName`) |
| Event handlers | noun + `EventHandler` or `Control_Click` Handles style |
| Event args classes | `EventArgs` suffix |
| Locals/parameters | camelCase |
| Private fields | camelCase; `m_` prefix optional in VB (Cory Smith) |
| Constants | PascalCase preferred over raw const (Cory Smith) |
| Avoid | `My`/`my` in identifiers; Hungarian on new .NET code |
| Shadowing | don't reuse outer-scope names |

### Language idioms (MS docs)

| Case | Rule |
|---|---|
| Options | `Option Strict On` + `Option Explicit On` per file |
| Strings | `$"..."` interpolation; StringBuilder in loops |
| Errors | Try/Catch/Using; never `On Error Goto` |
| Null check | `IsNot Nothing` not `Not ... Is Nothing` |
| Instantiation | `Dim x As New List(Of String)`; object initializers |
| Arrays | `Dim a As String() = {"a","b"}`; designator on type |
| Events | `Handles`; relaxed delegates when args unused |
| Shared | call via type name |
| LINQ | meaningful names; Where before Order; explicit Join |
| Modules | shared-only helpers → `Module` not static-only class |

### File & verify

| Case | Rule |
|---|---|
| File | one public type; filename = public class name |
| Folders | mirror namespace segments |
| Member order | visibility groups; alphabetize within group (Cory Smith) |
| Docs | `'''` XML on public members |
| Legacy | Wikibooks type-prefix vars (`iCount`) — VB6 only |

## Anti-patterns

- Missing Option Strict/Explicit on hand-written `.vb`
- Tab characters without space conversion
- Multiple statements per line with `:`
- Heavy explicit `_` continuation where implicit works
- `My` or `my` embedded in variable names
- Hungarian prefixes on new VB.NET (`strName`, `iCount`)
- `On Error Goto` instead of Try/Catch
- `Not x Is Nothing` instead of `x IsNot Nothing`
- Type suffix characters (`$`, `%`, `#`)
- Class with only Shared methods (use Module)
- `Microsoft.VisualBasic.Compatibility` APIs
- Single-letter names except obvious coordinates/index
- End-of-line comment blocks instead of `'` own-line (MS preference)
- Asterisk comment boxes
- Public API without XML documentation
- Multiple public types in one file
- LINQ join hidden in Where clause
- Bug fix without test/build verification

## Skill trace

| Artifact | Role |
|---|---|
| `vb-style-formatting-layout.md` | indent, statements, comments |
| `vb-style-naming-types.md` | PascalCase, interfaces, fields |
| `vb-style-idioms-control.md` | options, Try/Catch, LINQ, events |
| `vb-style-docs-verify.md` | XML docs, file layout, dotnet verify |
| `vb-coding-practices/SKILL.md` | Option Strict + dotnet format in CI |
