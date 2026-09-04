---
name: csharp-coding-practices
description: "Use when authoring or reviewing C#, Allman 4-space layout, file-scoped namespaces, Framework Design naming, modern C# idioms, specific exception handling, and XML docs on public API."
invocation: manual
disable-model-invocation: true
---

# C# Coding Practices

Application skill for C# /.NET style learning (from the archived `awesome-guidelines` style capsules). For ASP.NET/Blazor/MAUI patterns, load stack capsules in `skills/*-foundation`.

## Core Principle

C# readability is **Framework Design naming plus modern idioms enforced by EditorConfig/analyzers**, explicit public API, safe boolean ops, specific exceptions.

## When to Use / NOT

- C# application/library source, `.editorconfig`, Roslyn analyzers, `dotnet format` CI.
- Reviewing naming, layout, modern syntax, exception handling, XML docs.

**NOT when:**

- Non-C# code.
- Generated designer files, validate generators instead.
- F# / VB, different language conventions.

## Workflow

1. **Format & layout**, Allman braces, file-scoped namespace, usings (`csharp-style-formatting-layout.md`).
2. **Naming**, Pascal/camel, interfaces, suffixes (`csharp-style-naming-types.md`).
3. **Modern idioms**, var, collections, strings, required (`csharp-style-modern-idioms.md`).
4. **Exceptions & API**, catch, using, statics, XML docs (`csharp-style-exceptions-api.md`).
5. **Verify**, `dotnet format`, analyzer warnings as errors, tests on changed projects.

## Red Flags

- `using` inside namespace without `global::`
- Tabs or wrong brace style for project
- Hungarian notation or underscores in names
- `catch (Exception)` without strategy
- `var` when type not obvious
- `&`/`|` for boolean conditions
- Static call via derived type name
- Public API without XML summary
- `StatusEnum` / prefixed enum values

## Verification

- `dotnet format --verify-no-changes` on changed projects
- Analyzer/StyleCop/IDE rules per `.editorconfig`
- Capsule checklist on public API review


## References

- `awesome-guidelines/references/csharp-style-learning-note.md`
- `awesome-guidelines/references/csharp-style-formatting-layout.md`
- `awesome-guidelines/references/csharp-style-naming-types.md`
- `awesome-guidelines/references/csharp-style-modern-idioms.md`
- `awesome-guidelines/references/csharp-style-exceptions-api.md`
