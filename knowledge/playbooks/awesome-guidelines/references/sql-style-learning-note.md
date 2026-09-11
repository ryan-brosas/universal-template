# SQL style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `sql-style-*.md` capsules, `sql-scripting-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [SQL Style Guide (sqlstyle.guide)](https://www.sqlstyle.guide/) (primary) | snake_case identifiers; uppercase keywords; river alignment; `AS` on aliases; suffix conventions (`_id`, `_date`, `_status`); ISO 8601 dates; standard SQL portability; JOIN/subquery indentation; DDL constraint layout; avoid camelCase/Hungarian/plurals/OOP-in-SQL/EAV |
| Joe Celko *SQL Programming Style* (secondary, via sqlstyle.guide alignment) | consistent team style over anecdotes; readable identifiers; disciplined formatting |

**Not duplicated here:** Dialect-specific functions (MySQL `LIMIT` vs SQL Server `TOP`) — document dialect in project; prefer ANSI when portable. ORM-generated SQL — validate generator/migrations separately.

## Mental model

SQL style in this catalog is **readable relational text with portable ANSI habits**:

1. **Naming** — lowercase snake_case; collective table names (`staff`); singular columns; semantic suffixes; no `tbl_`/`sp_` prefixes.
2. **Query layout** — uppercase reserved words; keywords right-aligned “river”; 4-space DDL indent; explicit `AS` on aliases.
3. **DDL** — primary key first; constraints under columns; portable types (`NUMERIC` over float); CHECK validation separate.
4. **Patterns** — `BETWEEN`/`IN` over repeated `OR`; `CASE` for interpreted values; parameterized queries at application boundary (security probe in skill).

## Decision tables

### Naming

| Element | Rule |
|---|---|
| Tables | collective singular (`staff`, not `employees` if awkward) |
| Columns | singular lowercase snake_case |
| PK | avoid bare `id` when ambiguous; use `staff_num`, suffix `_id` |
| Aliases | meaningful; `AS` required; acronym from words (`s1`) |
| Procedures | verb name; no `sp_` prefix |
| Length | ≤30 chars; letters/numbers/underscore only |

### Suffixes (when applicable)

| Suffix | Meaning |
|---|---|
| `_id` | unique identifier |
| `_status` | flag/status |
| `_total` | sum |
| `_num` | numeric |
| `_name` | name field |
| `_date` | date |
| `_tally` | count |
| `_size` | size |
| `_addr` | address |

### Query formatting

| Topic | Rule |
|---|---|
| Keywords | `SELECT`, `FROM`, `WHERE` uppercase |
| Spacing | space around `=`, after commas, around string quotes |
| Line breaks | before `AND`/`OR`; after semicolons between statements |
| JOINs | indented past river; `ON` aligned |
| Subqueries | same river style; closing paren aligned when nested |

### DDL & types

| Topic | Rule |
|---|---|
| Types | prefer standard/portable; `NUMERIC`/`DECIMAL` over float |
| Dates | ISO 8601 storage |
| Defaults | same type as column; before `NOT NULL` |
| Keys | at least one key per table; named constraints |
| Avoid | EAV, value+unit split columns, OOP patterns in schema |

## Anti-patterns

- camelCase identifiers
- `tbl_orders`, `sp_getUser`
- quoted identifiers unless required
- bare `id` on every table
- lowercase `select`/`from`
- crowded one-line queries with no river
- alias without `AS`
- `FLOAT` for money
- EAV / arbitrary `UNION` when schema fix possible
- string-concatenated user input (injection)

## Skill trace

| Artifact | Role |
|---|---|
| `sql-style-naming-schema.md` | tables, columns, aliases, suffixes |
| `sql-style-query-layout.md` | keywords, river, joins, subqueries |
| `sql-style-ddl-types.md` | CREATE, types, constraints |
| `sql-style-query-patterns.md` | BETWEEN/IN/CASE, comments, portability |
| `sql-scripting-practices/SKILL.md` | sqlfluff/sqlparse/linter in CI |
