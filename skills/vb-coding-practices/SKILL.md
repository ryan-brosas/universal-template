---
name: vb-coding-practices
description: "Use when authoring or reviewing Visual Basic.NET, Option Strict/Explicit, 4-space layout, Framework PascalCase naming, Try/Catch idioms, XML docs on public API, and dotnet format/build/test in CI."
disable-model-invocation: true
---

# Visual Basic Coding Practices

Application skill for VB.NET style (archived `awesome-guidelines` capsules). Legacy VB6 Wikibooks Hungarian rules apply only when maintaining pre-.NET code.

## Core Principle

VB.NET quality is **Framework-aligned naming plus Strict options and readable blocks**, PascalCase public API, Try/Catch, no legacy On Error or Hungarian on new code.

## When to Use / NOT

- VB.NET libraries, WinForms/WPF/ASP.NET VB projects, `.vb` modules and classes.
- Setting up Option Strict, XML docs, `dotnet format`, analyzer/build CI.

**NOT when:**

- C# / F#, use language-specific practice skills.
- Pure VB6/VBA maintenance, Wikibooks Hungarian may apply locally; do not mix into new.NET modules without migration plan.

## Workflow

1. **Formatting**, indent, statements, comments (`vb-style-formatting-layout.md`).
2. **Naming**, PascalCase/camelCase, `m_` fields (`vb-style-naming-types.md`).
3. **Idioms**, options, Try/Catch, LINQ, events (`vb-style-idioms-control.md`).
4. **Docs/verify**, XML docs, file layout, build (`vb-style-docs-verify.md`).
5. **Verify**, `dotnet build`, `dotnet format`, tests on changed projects.

## Red Flags

- Missing Option Strict/Explicit on hand-written files
- Tab characters without space conversion
- Multiple statements per line (`:` separator)
- Heavy `_` continuation where implicit works
- `My` or `my` in identifier names
- Hungarian prefixes on new VB.NET (`strName`, `iCount`)
- `On Error Goto` instead of Try/Catch
- `Not x Is Nothing` instead of `x IsNot Nothing`
- Type suffix characters (`$`, `%`, `#`)
- Class containing only Shared methods (use Module)
- `Microsoft.VisualBasic.Compatibility` usage
- Single-letter names without clear geometric/index role
- Asterisk comment boxes
- End-of-line comment preference over own-line (MS style)
- Multiple public types in one file
- Public API without XML documentation
- LINQ join expressed only via Where
- Empty Else/Case Else without documented intent
- Bug fix without build/test verification

## Verification

- `dotnet build` on affected projects
- `dotnet format --verify-no-changes` when repo configures it
- Option Strict/Explicit header on new/changed `.vb`
- Public API XML doc spot-check
- Capsule checklist on legacy-vs-.NET naming boundary

## Skill Result Contract

```xml
<skill_result>
  <skill>vb-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>vb diff, dotnet build/format/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>Strict off waiver, Hungarian drift, missing XML, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/vb-style-learning-note.md`
- `awesome-guidelines/references/vb-style-formatting-layout.md`
- `awesome-guidelines/references/vb-style-naming-types.md`
- `awesome-guidelines/references/vb-style-idioms-control.md`
- `awesome-guidelines/references/vb-style-docs-verify.md`
