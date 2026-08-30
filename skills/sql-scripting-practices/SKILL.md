---
name: sql-scripting-practices
description: "Use when authoring or reviewing SQL — snake_case naming, uppercase keywords, river-aligned layout, portable DDL types, suffix conventions, and parameterized queries."
disable-model-invocation: true
---

# SQL Scripting Practices

Application skill for SQL style learning (`awesome-guidelines` deep ingest). For ORM-specific patterns (Django, Prisma, SQLAlchemy), load stack foundations.

## Core Principle

SQL readability is **consistent relational naming plus scannable layout** — river-aligned keywords, portable types, parameters at the app boundary.

## When to Use / NOT

- Hand-written migrations, analytics queries, views, stored procedures.
- Reviewing schema naming and query formatting in PRs.

**NOT when:**

- ORM-only codebases with no raw SQL — validate ORM/migration generator instead.
- NoSQL query languages.

## Workflow

1. **Naming** — tables, columns, aliases, suffixes (`sql-style-naming-schema.md`).
2. **Layout** — keywords, river, joins, subqueries (`sql-style-query-layout.md`).
3. **DDL** — CREATE, types, constraints (`sql-style-ddl-types.md`).
4. **Patterns** — BETWEEN/IN/CASE, comments, parameters (`sql-style-query-patterns.md`).
5. **Verify** — sqlfluff/SQLFluff or project linter + migration apply/dry-run on changed files.

## Red Flags

- camelCase or `tbl_`/`sp_` prefixes
- lowercase `select`/`from` in shared SQL
- missing `AS` on aliases
- `FLOAT` for money
- bare `id` everywhere
- EAV schema for relational data
- string-concatenated user input
- vendor-only functions without portability note

## Verification

- sqlfluff/sql-formatter on changed `.sql` files
- migration apply or `EXPLAIN` on touched queries
- Capsule checklist on schema/query review

## Skill Result Contract

```xml
<skill_result>
  <skill>sql-scripting-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>sql diff, linter/formatter output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>injection, non-portable DDL, unreadable layout, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/sql-style-learning-note.md`
- `awesome-guidelines/references/sql-style-naming-schema.md`
- `awesome-guidelines/references/sql-style-query-layout.md`
- `awesome-guidelines/references/sql-style-ddl-types.md`
- `awesome-guidelines/references/sql-style-query-patterns.md`
