---
name: strapi-foundation
description: Use when porting Strapi's DB-agnostic database kernel — knex-compiling query-builder state machine, lifecycle-hooked write pipeline with compensating rollback, per-subscriber hook-state threading, bounded identifier shortening, N+1-free batch populate, connect-order topological sorting, anyToOne relinking with document-sibling exclusion, hash-gated schema sync with 3-way DDL diffing, constraint-safe alter ladders, exactly-once migration runner, and dual-stream user/internal migration providers.
---
# Strapi: database-kernel foundation

## Use this for
Use when porting a DB-agnostic data layer over an SQL builder (knex-style): compiling a query DSL into SQL safely, keeping row writes consistent with link-table writes, threading hook state across before/after phases, generating deterministic DB identifiers under length limits, populating result pages without N+1, honoring positional relation connects, relinking exclusive polymorphic relations, synchronizing a declarative schema to a live database without destroying untracked tables, or running app and framework migrations exactly once. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/query-builder-knex-compilation.md` — how a query-intent state machine compiles to one knex query, including the sub-query rewrite for update/delete-with-joins.
- `references/entity-manager-write-pipeline.md` — how create/update/delete stay consistent without wrapping row + link writes in one transaction.
- `references/lifecycles-provider.md` — how before*/after* subscriber phases exchange state without globals.
- `references/identifier-shortener.md` — how table/column names always fit dialect identifier limits deterministically.
- `references/batch-populate-apply.md` — how to populate one attribute across a page of rows with a single join query and no N+1.
- `references/connect-array-orderer.md` — how positional `before/after` connects are resolved robustly (cycles, duplicates, missing anchors).
- `references/anytoone-relinking.md` — how exclusive anyToOne links are relinked without destroying sibling locale/draft documents.
- `references/schema-sync-gate.md` — how startup skips all DDL when migrations are settled and the persisted schema hash matches.
- `references/three-way-schema-diff.md` — how a safe DDL plan diffs live DB × previously-tracked schema × new schema without touching untracked user tables.
- `references/alter-table-ladder.md` — the FK-drop-first / recreate-last operation order that keeps constraint-touching DDL from aborting mid-flight.
- `references/special-type-conversions.md` — how dialect-specific lossy column changes run as raw SQL pre-passes that remove themselves from the diff.
- `references/schema-snapshot-storage.md` — how the last-synced schema is stored single-row and hashed order-insensitively.
- `references/migration-runner.md` — how pending migrations run sequentially exactly once with name+direction failure attribution.
- `references/migration-log-storage.md` — the lazy-create, log-after-success bookkeeping table contract behind the runner.
- `references/dual-provider-migrations.md` — how app-user and framework-internal migration streams coexist on separate tables in fixed order.

## Capsule map
**Query compilation**
- **query-builder-knex-compilation** — `getKnexQuery`: processState must run before shouldUseSubQuery; update/delete with joins rewrite as `whereIn('id', subquery)`; insert uses `returning('id')` only when dialect.useReturning().
**Write pipeline**
- **entity-manager-write-pipeline** — `create/update/delete`: lifecycles.run('before*') returns a States Map threaded to 'after*'; relation mutations run in their own transaction with compensating delete/revert of the main row on failure.
- **lifecycles-provider** — `run`: each subscriber owns one State entry keyed by subscriber identity; mutating `event.state` persists it into the Map passed to the matching after* phase.
**Schema naming**
- **identifier-shortener** — `getNameFromTokens` + `getShortenedName`: compressible tokens share budget evenly with surplus redistribution; overflow tokens become `prefix+shake256(name)` suffixes; maxLength=0 preserves legacy v4 names.
**Relation population & ordering**
- **batch-populate-apply** — `manyToMany` exemplar: select target rows joined to the link table with the link column aliased+renamed, then `groupBy(rename)` in memory; count mode groups in SQL; empty id sets early-return `[]`, never null.
- **connect-array-orderer** — `sortConnectArray`: recursive adjacency resolution with branch-scoped cycle detection, component-aware duplicate rejection, strict vs non-strict missing-anchor handling.
- **anytoone-relinking** — `deletePreviousAnyToOneRelations`: stale links deleted via `whereNotIn(inverseJoin, documentSiblingIds)` so other locales/statuses of the same document keep their links.
**Schema sync plane**
- **schema-sync-gate** — `SchemaProvider.sync`: migrations-first ordering bypasses the sha256 short-circuit; unchanged hash returns 'UNCHANGED' with zero inspector calls.
- **three-way-schema-diff** — `diffSchemas`: removals require previous-tracking evidence (`!isInUserSchema && wasTracked && !isReserved`); removed tables cascade to persisted `dependsOn` companions.
- **alter-table-ladder** — `updateSchema`/`alterTable`: one transaction inside start/endSchemaUpdate; FKs dropped first, columns dropped after FKs, indexes/FKs recreated last; MySQL drops an index implicitly with its FK.
- **special-type-conversions** — `handleSpecialTypeConversions`: postgres-only raw conversion SQL runs before the ladder and deletes its entry from `table.columns.updated` to prevent double processing.
- **schema-snapshot-storage** — `hashSchema/read/add`: tables sorted by name before sha256; single-row history via delete-then-insert; MySQL two-step id fetch (#20312).
**Migration plane**
- **migration-runner** — `createMigrationRunner.up`: pending = definition order minus executed name-set; `logMigration` strictly after successful `up`; failures wrapped `Migration <name> (<dir>) failed` with cause; `down` reverts exactly one step.
- **migration-log-storage** — `createStorage.executed`: lazily creates the `(id,name,time)` table when absent and returns `[]`; same factory backs `strapi_migrations` and `strapi_migrations_internal`.
- **dual-provider-migrations** — `createMigrationsProvider`: fixed [user, internal] order; only the user stream honors `runMigrations:false`; `.sql` migrations get raw-SQL up and a hard-rejected down; every body wrapped per-migration in `wrapTransaction`.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Strapi (`packages/core/database` non-EE portions, MIT Expat; repo carries an EE dual-license split), `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory project `strapi` (FULL mode, generation 2026-08-25T19:58:58Z, 88,379 nodes / 205,881 edges; 55 parse-partial files incl. `database/src/lifecycles/index.ts` range 8-8 and `schema/index.ts` range 11-11 — both verified by direct read; skipped=0). Pass 1 mined the kernel spine (query-builder → entity-manager → lifecycles → relations/populate); pass 2 added the schema-sync plane (`src/schema`) and migration plane (`src/migrations`).

## Full view (memory graph)
Revalidate `strapi` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Recorded pin: root `/mnt/hdd/utopia/inspo/strapi`, branch `develop`, HEAD `1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`, mode FULL, nodes 88,379 / edges 205,881. Caveats: `lifecycles/index.ts` is parse-partial at line 8 (type re-export only) and `schema/index.ts` at line 11 (`export type * from './types'` only); `packages/core/types` barrel index files are partially parsed — read flagged ranges directly before citing them.

## Boundaries
Adopt the pure contracts: intent-state→SQL compilation discipline, compensating write rollback, per-subscriber hook state, deterministic identifier compression, batch populate mapping, connect topological ordering, tracked-only schema removals, constraint-safe DDL ordering, exactly-once migration logging with fixed stream order. Adapt transaction scoping, dialect capability flags (`useReturning`, `supportsUnsigned`, postgres type-conversion SQL), reserved-table lists, and metadata shapes to your host ORM/knex version. Omit Strapi-specific product behavior: content-type UIDs, documents service semantics, admin/auth plane, the concrete 5.0.0 internal-migration bodies, EE features.
