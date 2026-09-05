---
name: java-coding-practices
description: "Use when authoring or reviewing Java, google-java-format layout, import discipline, Google naming, @Override, handled catches, static qualification, and Javadoc on public API."
invocation: manual
disable-model-invocation: true
---

# Java Coding Practices

Application skill for Java style learning (from the archived `awesome-guidelines` style capsules). For Spring/Jakarta/EE patterns, load stack capsules in `skills/*-foundation`.

## Core Principle

Follow the project formatter and API conventions. Google formatting is one
source-specific choice, not a reason to reformat an unrelated change. Review
exception handling for lost failures and intentional recovery.

## When to Use / NOT

- Java source, library public API, Checkstyle/google-java-format CI.
- Reviewing naming, imports, exception handling, Javadoc.

**NOT when:**

- Non-Java code.
- Generated sources, validate generator config instead.

## Workflow

1. **Format & imports**, use project settings. Google's 2-space/100-column and
   import rules apply when adopted (`java-style-formatting-imports.md`).
2. **Naming**, camelCase algorithm, constants discipline (`java-style-naming-types.md`).
3. **Practices**, `@Override`, catches, static qualify, null-safe equals (`java-style-exceptions-practices.md`).
4. **Docs**, Javadoc on public/protected API (`java-style-javadoc-public-api.md`).
5. **Verify**, formatter + Checkstyle (project rules) on changed paths.

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


## References

- `awesome-guidelines/references/java-style-learning-note.md`
- `awesome-guidelines/references/java-style-formatting-imports.md`
- `awesome-guidelines/references/java-style-naming-types.md`
- `awesome-guidelines/references/java-style-exceptions-practices.md`
- `awesome-guidelines/references/java-style-javadoc-public-api.md`
