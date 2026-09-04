---
name: delphi-coding-practices
description: "Use when authoring or reviewing Delphi/Object Pascal, 2-space layout, PascalCase T/I/E/F/A/L naming, dotted unit hierarchy, try/finally FreeAndNil, properties, XML docs, and IDE formatter in CI."
invocation: manual
disable-model-invocation: true
---

# Delphi Coding Practices

Application skill for Delphi/Object Pascal style learning (from the archived `awesome-guidelines` style capsules). Follow Embarcadero baseline; apply DelphiStandards namespace rules when project adopts them.

## Core Principle

Delphi quality is **PascalCase clarity + unit hierarchy + deterministic cleanup**, properties and docs on public surfaces, `FreeAndNil` in finally blocks.

## When to Use / NOT

- Delphi VCL/FMX apps, FireDAC services, Object Pascal libraries.
- Setting up IDE formatter, Pascal analyzer, DUnit/DUnitX tests in CI.

**NOT when:**

- Free Pascal/Lazarus-only dialect differences, document project baseline.
- Generated form `.dfm` designer output, validate hand-edited `.pas` only.

## Workflow

1. **Layout**, indent, begin/end, whitespace (`delphi-style-formatting-layout.md`).
2. **Naming**, T/I/E/F/A/L, PascalCase (`delphi-style-naming-types.md`).
3. **Units**, hierarchy, uses, structure (`delphi-style-units-structure.md`).
4. **Resources**, try/finally, except, docs (`delphi-style-resources-errors.md`).
5. **Verify**, compile, formatter, tests on changed units.

## Red Flags

- snake_case or underscores (non-API)
- Tab indentation
- Public fields on classes
- `.Free` without FreeAndNil pattern
- Empty except blocks
- Flat Unit1-style names in large apps
- Missing XML docs on exported API
- Implementation-only units in interface uses
- Heavy `with` statements

## Verification

- Project build (Win32/Win64 target)
- IDE formatter / `.editorconfig` indent=2
- DUnit/DUnitX or project test runner
- XML documentation compile (if enabled)
- Capsule checklist on new units


## References

- `awesome-guidelines/references/delphi-style-learning-note.md`
- `awesome-guidelines/references/delphi-style-formatting-layout.md`
- `awesome-guidelines/references/delphi-style-naming-types.md`
- `awesome-guidelines/references/delphi-style-units-structure.md`
- `awesome-guidelines/references/delphi-style-resources-errors.md`
