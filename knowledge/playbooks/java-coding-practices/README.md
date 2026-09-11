---
title: java-coding-practices
summary: Use when authoring or reviewing Java, google-java-format layout, import discipline, Google naming, @Override, handled catches, static qualification, and Javadoc on public API.
kind: playbook
---

# Java Coding Practices

Application skill for Java style. For Spring/Jakarta/EE patterns, load the framework's own source or docs.

## Core Principle

Follow the project formatter and API conventions. Google formatting is one choice
among valid project conventions, not a reason to reformat an unrelated change. Review
exception handling for lost failures and intentional recovery.

## When to Use / NOT

- Java source, library public API, Checkstyle/google-java-format CI.
- Reviewing naming, imports, exception handling, Javadoc.

**NOT when:**

- Non-Java code.
- Generated sources, validate generator config instead.

## Workflow

1. **Format & imports**, use project settings. Google's 2-space/100-column and
   import rules apply when adopted.
2. **Naming**, camelCase algorithm, constants discipline.
3. **Practices**, `@Override`, catches, static qualify, null-safe equals.
4. **Docs**, Javadoc on public/protected API.
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
