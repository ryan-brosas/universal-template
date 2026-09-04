---
name: fsharp-coding-practices
description: "Use when authoring or reviewing F#,.NET naming, XML docs, module/type design, Async/Task boundaries, vanilla.NET interop (Func, IEnumerable, TryGetValue), and Fantomas/dotnet build in CI."
invocation: manual
disable-model-invocation: true
---

# F# Coding Practices

Application skill for F# component design learning (from the archived `awesome-guidelines` style capsules). When targeting C# consumers, prioritize vanilla.NET API rules over F#-only idioms on the public surface.

## Core Principle

F# library quality is **audience-shaped APIs**, F#-facing modules and unions internally, BCL-friendly types and delegates on cross-language boundaries.

## When to Use / NOT

- F# libraries, SDKs, and shared `.fs` components consumed by F# or other.NET languages.
- Setting up Fantomas, XML doc warnings, `.fsi` for stable APIs, `dotnet build`/test in CI.

**NOT when:**

- Pure C# projects, use `csharp-coding-practices`.
- Generated FSharp.Core dependents only, validate hand-written public API.

## Workflow

1. **Names & docs**,.NET casing, `///` XML, `.fsi` if stable (`fsharp-style-naming-documentation.md`).
2. **Modules & types**, encapsulation, DUs, interfaces (`fsharp-style-modules-types.md`).
3. **Functions & async**, Async naming, extensions, constraints (`fsharp-style-functions-async.md`).
4. **Interop**, Func, IEnumerable, Task, null guards (`fsharp-style-dotnet-interop.md`).
5. **Verify**, Fantomas, `dotnet build`, optional C# consumer compile check on public API.

## Red Flags

- Public modules in cross-language NuGet libraries
- Exposed record/union cases on evolvable types
- Implementation inheritance for extension
- Custom symbolic operators without named API
- Public type abbreviations with wrong semantics
- SRTP/duck constraints on general consumer APIs
- `list`/`Map`/`option` in vanilla.NET public signatures
- Curried or tuple-returning public methods for C# consumers
- `int -> int` instead of `Func<int,int>` on public API
- Missing XML docs on exported members
- Overuse `[<AutoOpen>]`
- No null checks at vanilla.NET boundaries
- `[<CLIEvent>]` missing on public events

## Verification

- `dotnet format` / Fantomas check (project config)
- `dotnet build` with XML documentation warnings as errors (if enabled)
- Reflect or C# snippet compile against public API
- Capsule checklist on F#-facing vs vanilla.NET audience


## References

- `awesome-guidelines/references/fsharp-style-learning-note.md`
- `awesome-guidelines/references/fsharp-style-naming-documentation.md`
- `awesome-guidelines/references/fsharp-style-modules-types.md`
- `awesome-guidelines/references/fsharp-style-functions-async.md`
- `awesome-guidelines/references/fsharp-style-dotnet-interop.md`
