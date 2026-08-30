---
name: d-coding-practices
description: "Use when authoring or reviewing D, 4-space Allman layout, camelCase/PascalCase naming, alias= declarations, @property APIs, selective imports, Ddoc Params/Returns, and dub test/dfmt in CI."
disable-model-invocation: true
---

# D Coding Practices

Application skill for D style learning (from the archived `awesome-guidelines` style capsules). For Phobos contributions, follow full official dstyle Phobos section.

## Core Principle

D quality is **dstyle naming + explicit types/docs + tested modules**, properties and UFCS where idiomatic, not clever.

## When to Use / NOT

- D application/library modules, dub projects, Phobos-style contributions.
- Setting up dfmt, DScanner, dub test, coverage in CI.

**NOT when:**

- C/C++ code in same repo, use respective practice skills.
- Generated D bindings only, validate generator.

## Workflow

1. **Layout**, indent, braces, imports (`d-style-formatting-layout.md`).
2. **Naming**, modules, types, acronyms (`d-style-naming-types.md`).
3. **API**, alias, properties, UFCS (`d-style-declarations-api.md`).
4. **Docs & tests**, Ddoc, unittest, attributes (`d-style-docs-testing.md`).
5. **Verify**, dfmt, dub test, coverage on changed modules.

## Red Flags

- snake_case outside module names
- Tabs or lines >120 columns
- C-style reversed declarations (`int []x`)
- Meaningless type aliases
- get/set instead of `@property`
- UFCS on side-effect calls
- Non-conventional operator meanings
- Missing Ddoc on public API
- unittest inside templates
- Unsorted or overly global imports

## Verification

- dfmt check / project formatter
- `dub test` or project test runner
- `-cov` or project coverage gate on touched code
- ddox/Ddoc generation for public modules
- Capsule checklist on review

## Skill Result Contract

```xml
<skill_result>
  <skill>d-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>d diff, dub test/coverage output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>undocumented API, UFCS misuse, missing @safe, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/d-style-learning-note.md`
- `awesome-guidelines/references/d-style-formatting-layout.md`
- `awesome-guidelines/references/d-style-naming-types.md`
- `awesome-guidelines/references/d-style-declarations-api.md`
- `awesome-guidelines/references/d-style-docs-testing.md`
