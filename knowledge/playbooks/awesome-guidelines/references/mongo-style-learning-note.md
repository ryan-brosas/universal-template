# MongoDB data modeling — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `mongo-style-*.md` capsules, `mongodb-data-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [jsoendermann/MongoStyleGuide](https://github.com/jsoendermann/MongoStyleGuide) (primary) | Enums as UPPERCASE strings; boolean prefix is/has; day dates as `YYYY-MM-DD`; null vs undefined rules; camelCase keys; no ObjectId; object growth/nesting limits |
| [MongoDB data modeling best practices](https://www.mongodb.com/docs/manual/data-modeling/best-practices/) (secondary) | Embed vs reference decision table; duplicate data types; schema validation; index queried fields; atomicity; iterate schema early |
| `node-coding-practices` (secondary) | camelCase field names align with JS app layer consuming Mongo documents |
| `javascript-coding-practices` (secondary) | Application code typing/validation around BSON documents |

**Scope:** **Document schema design** for MongoDB collections — field types, naming, enums, null semantics, embed/reference patterns. **Not:** MongoDB server C++ style, aggregation pipeline SQL, or generic SQL (`sql-scripting-practices`).

## Mental model

Mongo schema quality is **self-documenting BSON** shaped for **read patterns**:

1. **Enums & booleans** — UPPERCASE string constants; explicit states never `null`; real booleans only with `is`/`has`/`did` prefix; merge exclusive flags into one enum.
2. **Dates, null, types** — BSON Date not ISO strings; calendar days as `YYYY-MM-DD`; `null` only for unset primitives; omit arrays/objects vs `null`; one type per field; numbers numeric except phone/ID strings.
3. **Names & IDs** — camelCase keys; plural camelCase collection names; dots for related collections; custom string `_id` over ObjectId.
4. **Modeling & verify** — prune flat growth; avoid deep nesting; embed vs reference by access pattern; validation + indexes on hot fields.

## Decision tables

### General (MongoStyleGuide)

| Topic | Rule |
|---|---|
| Surprise | Prefer understandable schema over writer convenience |
| Priorities | Optimize ease of development first unless proven scale need |

### Enumerations

| Topic | Rule |
|---|---|
| Representation | UPPERCASE string constants (`'MALE'`, `'WAITING'`) |
| Unknown states | Explicit enum value — never `null`, missing, or mixed types |
| Sets | Array of UPPERCASE enum strings |

### Booleans

| Topic | Rule |
|---|---|
| Two-state concepts | Use enum if not natural true/false or may grow beyond two values |
| Naming | Prefix `is`, `has`, `did` (e.g. `isDoctor`, `hasDiabetes`) |
| Orthogonality | Mutually exclusive booleans → single enum (`color: 'BLUE'`) |

### Dates

| Topic | Rule |
|---|---|
| Timestamps | BSON `Date` / ISODate — never ISO **strings** from JSON slip |
| Calendar days | `'YYYY-MM-DD'` string when time component irrelevant |

### Null and undefined

| Topic | Rule |
|---|---|
| Semantics | `null`/`undefined` mean **unset only** — not business states |
| Defaults | Use `''`, `0`, `[]` instead of null when sensible default exists |
| Primitives | absent → `null` (not missing in same column) |
| Objects/arrays | omit field when absent; don't use `null` or `[]` to mean N/A for typed absence |
| Mixed null/undefined | never in same column |
| Multiple absences | `{ state, value }` wrapper object |

### Other types

| Topic | Rule |
|---|---|
| Column typing | one BSON type per field |
| Object arrays | homogeneous schema across elements |
| Falsiness | don't use `0` or `''` as sentinel — use `null` |
| Numbers | numeric BSON; strings only for significant leading zeros (phone) |
| Units | `{ unit: 'KG', value: 10 }` not `'10 kg'` |
| ObjectId | avoid — use natural unique string or random string `_id` |

### Names

| Topic | Rule |
|---|---|
| Fields | camelCase (not snake_case) |
| Abbreviations | avoid except domain DSL (`ABIRight`, `HISNumber`) |
| Collections | plural camelCase; dot notation for related (`users.appointments`) |

### Object modeling (MongoStyleGuide + MongoDB official)

| Topic | Rule |
|---|---|
| Growth | prune/merge into nested objects (`assessmentStates.foot`) |
| Nesting depth | break up excessively nested documents |
| Embed | query together, has-a, update together, bounded size |
| Reference | high cardinality child, unbounded growth, independent lifecycle |
| Duplication | OK for immutable/temporal; watch staleness-sensitive fields |
| Validation | `$jsonSchema` on critical fields/types/enums |
| Indexes | fields used in filter, sort, `$lookup` |

## Anti-patterns

- Numeric or boolean enums (`gender: 1`, `gender: true`)
- Title-case enum strings mixed with UPPERCASE constants
- `null` as enum "unknown" state
- Mutually exclusive boolean triplets (`isRed`, `isBlue`, `isGreen`)
- ISO date strings in persisted documents
- `Date` type for birthdate-only fields
- Overloading `null`/`undefined` with business meaning
- `null` vs missing mixed in same field across docs
- `null` for empty notes/comments when `''`/`[]` default fits
- Mixed types in one field (`1`, `'2'`, `{ value: 3 }`)
- Heterogeneous object shapes in array columns
- `height: 0` as "unknown"
- Numeric strings for arithmetic fields
- ObjectId `_id` when app layer struggles with serialization
- snake_case field keys in JS-first stacks
- Unbounded embedded arrays (lessons → separate collection when formats explode)
- Distributed transactions as substitute for bad embed/reference choice
- No index on hot query paths

## Skill trace

| Artifact | Role |
|---|---|
| `mongo-style-enums-booleans.md` | UPPERCASE enums, boolean rules |
| `mongo-style-dates-null-types.md` | dates, null, homogeneous types |
| `mongo-style-names-ids.md` | camelCase, collections, _id |
| `mongo-style-modelling-verify.md` | nesting, embed/reference, validation |
| `mongodb-data-practices/SKILL.md` | schema review workflow |

## Relation to sibling skills

| MongoStyleGuide | MongoDB official docs |
|---|---|
| Field-level conventions | Embed/reference tradeoffs |
| No ObjectId opinion | May suggest explicit _id for small docs |
| camelCase JS alignment | Performance, indexes, validation |
| Ease of development first | Plan early, iterate |
