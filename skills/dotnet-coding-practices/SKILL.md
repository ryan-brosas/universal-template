---
name: dotnet-coding-practices
description: "Use when designing or reviewing cross-language .NET public APIs — Framework Design naming, scenario-driven library design, exception/event/dispose patterns, secure coding baseline, and analyzer/CLS gates in CI."
disable-model-invocation: true
---

# .NET Coding Practices

Cross-cutting application skill for Framework Design Guidelines + secure coding (from the archived `awesome-guidelines` style capsules). For language syntax, load `csharp-coding-practices`, `vb-coding-practices`, or `fsharp-coding-practices`.

## Core Principle

.NET library quality is **scenario-first public API with FDG naming and modern security boundaries** — no CAS/binary formatters, specific exceptions, aggregate entry types.

## When to Use / NOT

- Shared .NET libraries, NuGet packages, multi-language solutions, public API reviews.
- Naming namespaces/types, designing aggregate components, security baseline audits.

**NOT when:**

- C#/VB/F# formatting-only changes — use language practice skills.
- Non-.NET stacks.
- Generated designer/proxy code — validate generators.

## Workflow

1. **Naming** — Pascal/camel, affixes, namespaces (`dotnet-style-naming-framework.md`).
2. **API design** — scenarios, aggregates, collections (`dotnet-style-api-design.md`).
3. **Exceptions/events** — throw/catch, dispose (`dotnet-style-exceptions-events.md`).
4. **Security/verify** — CAS ban, input hardening, analyzers (`dotnet-style-security-verify.md`).
5. **Language pass** — route to C#/VB/F# skill for syntax/layout.
6. **Verify** — analyzers, CLS, build/tests on changed assemblies.

## Red Flags

- Org-chart namespace hierarchy
- Abstract base gets the best feature-area name
- Simple scenario needs many instantiated types
- Hungarian notation or underscores in public API
- Public fields
- Arrays/`List<T>`/`Dictionary<,>` in public API instead of collection types
- Throwing `Exception`/`SystemException`
- Catching `Exception` without strategy
- Error codes instead of exceptions
- `Before*`/`After*` event naming
- `StatusEnum` or prefixed enum members
- Interface without concrete implementation and consumer
- Sealed/virtual without documented reason
- Mutable public value types
- BinaryFormatter, Remoting, DCOM, APTCA, partial trust
- Unvalidated external/path input
- Native wrapper granting unmanaged rights broadly
- Library missing CLS/analyzer gate
- Duplicating FDG rules only in language skill without this cross-cut

## Verification

- Roslyn analyzers / FxCop-style rules on changed libraries
- `[CLSCompliant(true)]` where applicable
- Scenario sample code uses intended aggregate type
- Banned API grep clean on new code
- `dotnet build` + tests on touched projects
- Capsule checklist on public API additions

## Skill Result Contract

```xml
<skill_result>
  <skill>dotnet-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>public API diff, analyzer/build output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>legacy serializer, weak input validation, or FDG naming drift</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/dotnet-style-learning-note.md`
- `awesome-guidelines/references/dotnet-style-naming-framework.md`
- `awesome-guidelines/references/dotnet-style-api-design.md`
- `awesome-guidelines/references/dotnet-style-exceptions-events.md`
- `awesome-guidelines/references/dotnet-style-security-verify.md`

## Language routing

- C# layout/idioms → `csharp-coding-practices`
- Visual Basic .NET → `vb-coding-practices`
- F# → `fsharp-coding-practices`
