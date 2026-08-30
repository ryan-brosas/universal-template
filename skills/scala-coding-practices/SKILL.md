---
name: scala-coding-practices
description: "Use when authoring or reviewing Scala, 2-space layout, camelCase naming, accessor/mutator conventions, explicit public types, immutable case classes, Option over null, and Scaladoc on public API."
disable-model-invocation: true
---

# Scala Coding Practices

Application skill for Scala style learning (from the archived `awesome-guidelines` style capsules). For Spark/Akka/ZIO stack patterns, load stack capsules in `foundation-pack/`.

## Core Principle

Scala readability is **official layout/naming plus functional safety**, immutable data, explicit public types, expression-oriented control, documented API.

## When to Use / NOT

- Scala application/library source, Scalafmt/Scalafix/wartremover CI.
- Reviewing naming, types, case classes, control flow, Scaladoc.

**NOT when:**

- Non-Scala code.
- Generated boilerplate, validate generators instead.
- Spark-internal perf micro-optimizations, use Databricks guide in stack capsules in `foundation-pack/`.

## Workflow

1. **Format & layout**, 2-space, wraps, control spacing (`scala-style-formatting-layout.md`).
2. **Naming**, packages, accessors, parentheses (`scala-style-naming-packages.md`).
3. **Types**, inference rules, immutability, Option (`scala-style-types-immutability.md`).
4. **Control & docs**, return, for, Scaladoc, errors (`scala-style-control-api.md`).
5. **Verify**, Scalafmt/Scalafix + `sbt test` / `sbt compile` on changed modules.

## Red Flags

- Tabs or 4-space indent
- Java getter/setter names in Scala API
- Side-effect nullary method without `()`
- Symbolic operators in domain API
- `var` in case class
- Missing `override`
- Public method without return type
- `Option.get` / `null`
- `return` in closures
- Public API without Scaladoc

## Verification

- Scalafmt/Scalafix on changed files
- Compile + tests for touched projects
- Capsule checklist on public API review

## Skill Result Contract

```xml
<skill_result>
  <skill>scala-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>scala diff, scalafmt/scalafix output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>return in closure, Option.get, missing public type, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/scala-style-learning-note.md`
- `awesome-guidelines/references/scala-style-formatting-layout.md`
- `awesome-guidelines/references/scala-style-naming-packages.md`
- `awesome-guidelines/references/scala-style-types-immutability.md`
- `awesome-guidelines/references/scala-style-control-api.md`
