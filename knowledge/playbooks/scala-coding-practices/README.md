---
title: scala-coding-practices
summary: Use when authoring or reviewing Scala, 2-space layout, camelCase naming, accessor/mutator conventions, explicit public types, immutable case classes, Option over null, and Scaladoc on public API.
kind: playbook
---

# Scala Coding Practices

Application skill for Scala style. For Spark/Akka/ZIO stack patterns, load the framework's own source or docs.

## Core Principle

Scala readability is **official layout/naming plus functional safety**, immutable data, explicit public types, expression-oriented control, documented API.

## When to Use / NOT

- Scala application/library source, Scalafmt/Scalafix/wartremover CI.
- Reviewing naming, types, case classes, control flow, Scaladoc.

**NOT when:**

- Non-Scala code.
- Generated boilerplate, validate generators instead.
- Spark-internal perf micro-optimizations, use the Databricks guide.

## Workflow

1. **Format & layout**, 2-space, wraps, control spacing.
2. **Naming**, packages, accessors, parentheses.
3. **Types**, inference rules, immutability, Option.
4. **Control & docs**, return, for, Scaladoc, errors.
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
