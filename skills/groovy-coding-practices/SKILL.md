---
name: groovy-coding-practices
description: "Use when authoring or reviewing Groovy — idiomatic syntax (no semicolons, POGOs, GDK, GStrings), with/tap, Groovy truth and safe nav, strong public typing, and CodeNarc/npm-groovy-lint in CI."
disable-model-invocation: true
---

# Groovy Coding Practices

Application skill for Groovy style learning (`awesome-guidelines` deep ingest). For Grails-specific conventions, combine with stack foundations and project CodeNarc rulesets.

## Core Principle

Groovy quality is **idiomatic expressiveness with typed public seams** — GDK and property syntax internally, explicit types on shared API.

## When to Use / NOT

- Groovy scripts, Gradle plugins, Grails apps, JVM automation libraries.
- Setting up CodeNarc, npm-groovy-lint, Spock tests in CI.

**NOT when:**

- Pure Java/Kotlin modules — use language-specific practice skills.
- Generated AST/transform output — validate generators.

## Workflow

1. **Syntax** — semicolons, def, parens, strings (`groovy-style-syntax-idioms.md`).
2. **Objects** — POGOs, with/tap, equality (`groovy-style-objects-properties.md`).
3. **Collections** — GDK, truth, nav (`groovy-style-collections-gdk.md`).
4. **API** — public typing, assert (`groovy-style-typing-api.md`).
5. **Verify** — CodeNarc/npm-groovy-lint, compile, tests on changed sources.

## Red Flags

- Semicolons on every line
- `def String` / `def` constructors
- Redundant `public` everywhere
- `each() { }` with empty parens
- Manual getter/setter boilerplate on POGOs
- String `+` where GString fits
- Nested null checks vs `?.`
- `==` for reference identity
- Untyped public `def` methods
- Accidental return from assignment in `def` methods
- Java `.class` literals where unnecessary
- Obsolete `Vector`/`Hashtable`
- Blanket `catch (any)` without justification

## Verification

- CodeNarc / npm-groovy-lint (project ruleset)
- `./gradlew compileGroovy` or project build
- Spock/JUnit tests on changed modules
- Capsule checklist on public method signatures

## Skill Result Contract

```xml
<skill_result>
  <skill>groovy-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>groovy diff, CodeNarc/lint/build/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>accidental def return, null NPE, weak public API, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/groovy-style-learning-note.md`
- `awesome-guidelines/references/groovy-style-syntax-idioms.md`
- `awesome-guidelines/references/groovy-style-objects-properties.md`
- `awesome-guidelines/references/groovy-style-collections-gdk.md`
- `awesome-guidelines/references/groovy-style-typing-api.md`
