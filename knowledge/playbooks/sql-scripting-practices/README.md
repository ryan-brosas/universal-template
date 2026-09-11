---
title: sql-scripting-practices
summary: Use when authoring or reviewing SQL, snake_case naming, uppercase keywords, river-aligned layout, portable DDL types, suffix conventions, and parameterized queries.
kind: playbook
---

# SQL Scripting Practices

Application skill for SQL style. For ORM-specific patterns (Django, Prisma, SQLAlchemy), consult the ORM's own source or docs.

## Core Principle

SQL readability is **consistent relational naming plus scannable layout**, river-aligned keywords, portable types, parameters at the app boundary.

## When to Use / NOT

- Hand-written migrations, analytics queries, views, stored procedures.
- Reviewing schema naming and query formatting in PRs.

**NOT when:**

- ORM-only codebases with no raw SQL, validate ORM/migration generator instead.
- NoSQL query languages.

## Workflow

1. **Naming**, tables, columns, aliases, suffixes.
2. **Layout**, keywords, river, joins, subqueries.
3. **DDL**, CREATE, types, constraints.
4. **Patterns**, BETWEEN/IN/CASE, comments, parameters.
5. **Verify**, sqlfluff/SQLFluff or project linter + migration apply/dry-run on changed files.

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
