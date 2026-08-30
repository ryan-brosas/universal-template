---
name: java-coding-practices
description: "Use when authoring or reviewing Java — google-java-format layout, import discipline, Google naming, @Override, handled catches, static qualification, and Javadoc on public API."
disable-model-invocation: true
---

# Java Coding Practices

Application skill for Java style learning (`awesome-guidelines` deep ingest). For Spring/Jakarta/EE patterns, load stack foundations.

## Core Principle

Java readability is **mechanical Google format plus explicit API contracts** — formatted consistently, imports explicit, overrides annotated, catches never silent.

## When to Use / NOT

- Java source, library public API, Checkstyle/google-java-format CI.
- Reviewing naming, imports, exception handling, Javadoc.

**NOT when:**

- Non-Java code.
- Generated sources — validate generator config instead.

## Workflow

1. **Format & imports** — 2-space, 100 cols, braces, no star imports (`java-style-formatting-imports.md`).
2. **Naming** — camelCase algorithm, constants discipline (`java-style-naming-types.md`).
3. **Practices** — `@Override`, catches, static qualify, null-safe equals (`java-style-exceptions-practices.md`).
4. **Docs** — Javadoc on public/protected API (`java-style-javadoc-public-api.md`).
5. **Verify** — formatter + Checkstyle (project rules) on changed paths.

## Red Flags

- `import foo.*`
- Empty catch without comment
- `mField` / Hungarian prefixes
- Missing `@Override` on interface impl
- `instance.staticMethod()`
- Public API without Javadoc summary

## Verification

- google-java-format / project formatter check
- Checkstyle or equivalent on changed modules
- Capsule checklist on public API review

## Skill Result Contract

```xml
<skill_result>
  <skill>java-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>java diff, format/checkstyle output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>star import, silent catch, missing override, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/java-style-learning-note.md`
- `awesome-guidelines/references/java-style-formatting-imports.md`
- `awesome-guidelines/references/java-style-naming-types.md`
- `awesome-guidelines/references/java-style-exceptions-practices.md`
- `awesome-guidelines/references/java-style-javadoc-public-api.md`
