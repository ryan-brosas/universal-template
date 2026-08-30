# C# / .NET style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `csharp-style-*.md` capsules, `csharp-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [C# Coding Conventions](https://learn.microsoft.com/en-us/dotnet/csharp/fundamentals/coding-style/coding-conventions) (primary) | 4-space Allman braces; file-scoped namespaces; usings outside namespace; `var` when obvious; catch specific exceptions; `&&`/`||`; collection expressions; raw strings; `using` disposal; qualify statics; XML docs on public members |
| [.NET Naming Guidelines](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/naming-guidelines) + [Capitalization](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/capitalization-conventions) + [General naming](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/general-naming-conventions) | PascalCase types/members; camelCase parameters; `I` prefix interfaces; no underscores/Hungarian; CLR type names in API; compound word table (`FileName`, `LogOn`); case-insensitive CLR constraint |
| [Names of Classes, Structs, Interfaces](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/names-of-classes-structs-and-interfaces) (secondary) | nouns for types; `I` interfaces; `Exception`/`EventArgs`/`Attribute` suffixes; generic `T`/`TSession`; enum singular/plural rules |

**Not duplicated here:** Full `.editorconfig` matrix — project EditorConfig wins. ASP.NET/Blazor patterns — use stack foundations.

## Mental model

C# style in this catalog is **Framework Design naming plus modern C# idioms enforced mechanically**:

1. **Layout** — 4 spaces, Allman braces, one statement/declaration per line, file-scoped namespace, usings outside namespace.
2. **Naming** — PascalCase for types/members; camelCase parameters/locals; `I` interfaces; suffix rules (`Exception`, `Async` in modern code); no Hungarian/underscores.
3. **Modern C#** — collection expressions, interpolated strings, target-typed `new`, `required` init, `&&`/`||`, `using` declarations, language keywords (`string`, `int`).
4. **API & errors** — XML docs on public surface; catch specific types; static calls qualified by declaring type.

## Decision tables

### Formatting (C# conventions)

| Topic | Rule |
|---|---|
| Indent | 4 spaces, spaces not tabs |
| Braces | Allman — `{` on own line aligned with control |
| Namespace | file-scoped `namespace Foo;` when single namespace |
| Usings | outside namespace (avoid context-sensitive resolution) |
| Statements | one per line; one declaration per line |
| Comments | `//` single-line; XML on public API |

### Naming (Framework Design)

| Element | Convention |
|---|---|
| Namespace/type/method/property | PascalCase |
| Parameter/local | camelCase |
| Interface | `I` + PascalCase (`IEnumerable`) |
| Constant/static readonly | PascalCase |
| Generic param | `T` or `T` + role (`TSession`) |
| Acronyms | 2-letter both caps (`IOStream`); longer capitalize first only |
| Compound words | closed form (`Endpoint`, not `EndPoint`) |

### Type suffixes

| Base | Suffix |
|---|---|
| `Exception` | `…Exception` |
| `Attribute` | `…Attribute` |
| `EventArgs` | `…EventArgs` |
| `EventHandler` delegate | `…EventHandler` |
| Collections | `…Collection` / `…Dictionary` |

### Modern idioms

| Case | Rule |
|---|---|
| `var` | only when type obvious from RHS (`new`, literal, cast) |
| foreach | explicit element type |
| Strings | interpolation / raw string literals |
| Collections | collection expressions `[ … ]` |
| Logic | `&&`/`||` not `&`/`|` for boolean |
| Dispose | `using` declaration |
| Exceptions | specific catch; rethrow with `throw;` |
| Statics | `TypeName.Member()` |

## Anti-patterns

- Tabs or K&R braces when team uses Allman EditorConfig
- `using` inside namespace (context-sensitive breakage)
- `catch (Exception)` without filter/rethrow strategy
- Hungarian (`strName`, `iCount`)
- Underscores in identifiers
- `var` when type not obvious from expression
- `MyClass.BaseStatic()` through derived type name
- Public API without XML summary
- Enum named `StatusEnum` or values prefixed `adActive`

## Skill trace

| Artifact | Role |
|---|---|
| `csharp-style-formatting-layout.md` | indent, braces, namespace, usings |
| `csharp-style-naming-types.md` | Pascal/camel, interfaces, suffixes |
| `csharp-style-modern-idioms.md` | var, collections, strings, using, && |
| `csharp-style-exceptions-api.md` | catch, XML docs, static qualify |
| `csharp-coding-practices/SKILL.md` | EditorConfig/analyzers in CI |
