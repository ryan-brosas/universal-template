# F# style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `fsharp-style-*.md` capsules, `fsharp-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Microsoft F# component design guidelines](https://learn.microsoft.com/en-us/dotnet/fsharp/style-guide/component-design-guidelines) (primary) | .NET naming table; XML docs; `.fsi` for stable APIs; F#-facing vs vanilla .NET library split; modules/namespaces; hide record/union reps; interfaces over inheritance; `Async`/`AsyncCompute`; extension members; union trees; limit SRTP/inline constraints; avoid custom operators; interop: `Func`, TryGetValue, `IEnumerable`, `Task`, null checks, no currying/tuples |
| [F# Component Design Guidelines v14 (PDF)](https://fsharp.org/specs/component-design-guidelines/fsharp-design-guidelines-v14.pdf) (secondary) | confirms dual-audience design; five principles alignment; CompiledName for .NET consumers |

**Not duplicated here:** Full .NET Framework Design Guidelines — follow as fallback. WPF/WinForms UI patterns — use stack foundations.

## Mental model

F# component design is **audience-first API shaping**:

1. **Pick audience** — F#-facing (modules, unions, `Async`, options) vs vanilla .NET (namespaces, classes, `Task`, `Func`, TryGetValue).
2. **Naming & docs** — .NET capitalization; PascalCase types; camelCase parameters; `///` XML on public API; consider `.fsi` when API stabilizes.
3. **Types** — hide evolving record/union representations; prefer interfaces over implementation inheritance; DUs for tree data; avoid public type abbreviations that leak semantics.
4. **Functions** — intrinsic ops as methods/properties; `AsyncOperation` naming; small tuples OK; named types for larger returns; extension members for BCL idioms.
5. **Interop** — `seq<T>`/`IEnumerable<T>` not F# lists in public vanilla API; overloads not optional args; null guards at boundary; `CompiledName` judiciously.

## Decision tables

### Universal

| Topic | Rule |
|---|---|
| Baseline | [.NET Library Design Guidelines](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/) |
| Docs | `///` XML on public types/members |
| Stable API | `.fsi` signature files when surface is frozen |
| Strings | state cultural intent for compare/convert |

### Naming (F#-facing)

| Entity | Convention |
|---|---|
| Types/modules (public to .NET) | PascalCase |
| Parameters/locals | camelCase |
| Union cases | PascalCase, no prefix in public API |
| Generics | `T`, `U`, `Key`, `Value` — PascalCase |
| Abbreviations | avoid in public component design |
| Module values | camelCase when keyword-like (`invalidArg`); PascalCase when .NET-visible |

### Module & type design

| Case | Rule |
|---|---|
| Organization | `namespace` or top-level `module` per file |
| Mutable state | classes with private `let mutable` |
| Polymorphism | interfaces, not inheritance hierarchies |
| Collections module | `Type.map` / `Type.iter` pattern |
| Custom modules extending Core | `[<RequireQualifiedAccess>]` |
| AutoOpen | sparingly — extension/math DSL modules only |
| Records/unions | private or signature-hidden if design may evolve |
| Operators | named members first; symbolic operators rarely |

### Signatures & async (F#-facing)

| Case | Rule |
|---|---|
| Multi-return | small unrelated tuple OK; else named type |
| Async public API | `Async<'T>` or `OperationAsync` → `Task` for .NET |
| Extension members | BCL idioms (`TryGet`, `AsyncReceive`) |
| Numeric generics | inline + member constraints in math libs only |
| Duck typing via constraints | avoid in public F# libraries |

### Vanilla .NET public API

| Case | Rule |
|---|---|
| Structure | `namespace` + types only; no public modules |
| Utilities | `[<AbstractClass; Sealed>]` static holder vs module |
| Delegates | `Func`/`Action` not `int -> int` in public members |
| Options | TryGetValue bool+out, not `option` return |
| Optional args | overloads, not F# optional parameters |
| Collections | `IEnumerable<T>` / `seq<T>` in signatures |
| Async | `Task` / `StartAsTask`; cancellation token when needed |
| Returns | named types or out params — not tuples |
| Parameters | tupled .NET style — no currying |
| Null | guard at API boundary (`nullArg`, `| null` in F# 9+) |
| Events | `[<CLIEvent>]` + `DelegateEvent<EventHandler<_>>` |
| Unions | private + factory members / active patterns for C# |

## Anti-patterns

- Public F# modules in vanilla .NET libraries
- Exposed record/union cases when API may version
- Implementation inheritance for extensibility
- Custom symbolic operators in public libraries
- Public type abbreviations (`type MultiMap = Map<_, list>`) with wrong semantics
- SRTP/duck-typing constraints on consumer-facing APIs
- `list<'T>` / `Map` in cross-language public signatures
- F# option types in vanilla .NET public API
- Curried public methods
- Tuple returns in vanilla .NET API
- Missing XML docs on NuGet-facing surface
- Overuse `[<AutoOpen>]` polluting namespaces
- `FSharpFunc` leaking to C# consumers

## Skill trace

| Artifact | Role |
|---|---|
| `fsharp-style-naming-documentation.md` | .NET names, XML, `.fsi` |
| `fsharp-style-modules-types.md` | modules, classes, interfaces, unions |
| `fsharp-style-functions-async.md` | signatures, Async, extensions, constraints |
| `fsharp-style-dotnet-interop.md` | vanilla .NET API façade rules |
| `fsharp-coding-practices/SKILL.md` | Fantomas/diagnostics/dotnet build in CI |
