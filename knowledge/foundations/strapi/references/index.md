<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->

# Strapi: database-kernel foundation

## Use this for
Use when porting a DB-agnostic data layer over an SQL builder (knex-style): compiling a query DSL into SQL safely, keeping row writes consistent with link-table writes, threading hook state across before/after phases, generating deterministic DB identifiers under length limits, populating result pages without N+1, honoring positional relation connects, relinking exclusive polymorphic relations, synchronizing a declarative schema to a live database without destroying untracked tables, running app and framework migrations exactly once, sorting by computed status or joined-relation columns with stable pagination, building DB metadata from model configs, or keeping exclusive polymorphic links consistent. Also covers the data-transfer plane: orchestrating multi-stage streaming transfers with per-stage skip/cancel/rollback, reporting progress without consuming the streams, ordering an untrusted WebSocket step protocol with a single-stage lock, making request/response idempotent under timeouts via uuid dedup-replay, and evolving binary-over-JSON wire formats across mixed-version peers. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./query-builder-knex-compilation.md` — how a query-intent state machine compiles to one knex query, including the sub-query rewrite for update/delete-with-joins.
- `./entity-manager-write-pipeline.md` — how create/update/delete stay consistent without wrapping row + link writes in one transaction.
- `./lifecycles-provider.md` — how before*/after* subscriber phases exchange state without globals.
- `./identifier-shortener.md` — how table/column names always fit dialect identifier limits deterministically.
- `./batch-populate-apply.md` — how to populate one attribute across a page of rows with a single join query and no N+1.
- `./connect-array-orderer.md` — how positional `before/after` connects are resolved robustly (cycles, duplicates, missing anchors).
- `./anytoone-relinking.md` — how exclusive anyToOne links are relinked without destroying sibling locale/draft documents.
- `./status-sort-expression.md` — how a virtual `status` sort key becomes a parameterized CASE rank that survives SELECT DISTINCT.
- `./deep-sort-wrap.md` — how row-number partition wrapping dedupes parents when sorting by joined-relation columns while keeping pagination correct.
- `./metadata-load-models.md` — how model configs become DB metadata in three passes without double-processing identifier names.
- `./morph-one-cascade-delete.md` — how exclusive morphOne links are re-derived from incoming rows when a morphToMany collection is rewritten.
- `./schema-sync-gate.md` — how startup skips all DDL when migrations are settled and the persisted schema hash matches.
- `./three-way-schema-diff.md` — how a safe DDL plan diffs live DB × previously-tracked schema × new schema without touching untracked user tables.
- `./alter-table-ladder.md` — the FK-drop-first / recreate-last operation order that keeps constraint-touching DDL from aborting mid-flight.
- `./special-type-conversions.md` — how dialect-specific lossy column changes run as raw SQL pre-passes that remove themselves from the diff.
- `./schema-snapshot-storage.md` — how the last-synced schema is stored single-row and hashed order-insensitively.
- `./migration-runner.md` — how pending migrations run sequentially exactly once with name+direction failure attribution.
- `./migration-log-storage.md` — the lazy-create, log-after-success bookkeeping table contract behind the runner.
- `./dual-provider-migrations.md` — how app-user and framework-internal migration streams coexist on separate tables in fixed order.
- `./transfer-engine-stage-pipeline.md` — how a fixed-order multi-stage streaming transfer gets per-stage skip, mid-stage cancellation, and destination-only rollback.
- `./progress-reporting-plane.md` — how per-stage count/bytes/ETA are measured with stream-replacing trackers that never consume or buffer the payload.
- `./remote-push-flow-state-machine.md` — how an untrusted WS step protocol is kept ordered and single-stage by an index-difference flow plus lock/unlock.
- `./ws-uuid-replay-dispatch.md` — how request/response over a fire-and-forget socket stays idempotent when the client resends the same uuid.
- `./asset-chunk-wire-negotiation.md` — how a binary-over-JSON wire format evolves (base64 vs legacy Buffer.toJSON) via init-echo negotiation and a union decode ladder.

## Capsule map
**Metadata plane**
- **metadata-load-models** — `loadModels`: three passes over `cloneDeep(models)` (init with identifier-resolved tableName → build relations/attributes with context-wrapped errors → derive `columnToAttribute` reverse map); preset `columnName` is never re-shortened; `validate()` throws on duplicate table names at load time.
**Query compilation**
- **query-builder-knex-compilation** — `getKnexQuery`: processState must run before shouldUseSubQuery; update/delete with joins rewrite as `whereIn('id', subquery)`; insert uses `returning('id')` only when dialect.useReturning().
**Ordering & deep sort**
- **status-sort-expression** — `buildStatusSortExpression`: parameterized CASE rank (0 draft-only / 1 modified / 2 published) over correlated `document_id` subqueries; the identical raw expression must be duplicated into the SELECT list under DISTINCT (#26746); i18n models carry a locale guard.
- **deep-sort-wrap** — `wrapWithDeepSort`: baseQuery keeps filters but loses select/order/pagination; T numbers rows per parent id; resultQuery inner-joins T on `row_number = 1`, re-applies pagination outside, appends `T.id ASC` tie-breaker; deep sort + deep filter is a documented unsupported combination.
**Write pipeline**
- **entity-manager-write-pipeline** — `create/update/delete`: lifecycles.run('before*') returns a States Map threaded to 'after*'; relation mutations run in their own transaction with compensating delete/revert of the main row on failure.
- **lifecycles-provider** — `run`: each subscriber owns one State entry keyed by subscriber identity; mutating `event.state` persists it into the Map passed to the matching after* phase.
**Schema naming**
- **identifier-shortener** — `getNameFromTokens` + `getShortenedName`: compressible tokens share budget evenly with surplus redistribution; overflow tokens become `prefix+shake256(name)` suffixes; maxLength=0 preserves legacy v4 names.
**Relation population & ordering**
- **batch-populate-apply** — `manyToMany` exemplar: select target rows joined to the link table with the link column aliased+renamed, then `groupBy(rename)` in memory; count mode groups in SQL; empty id sets early-return `[]`, never null.
- **connect-array-orderer** — `sortConnectArray`: recursive adjacency resolution with branch-scoped cycle detection, component-aware duplicate rejection, strict vs non-strict missing-anchor handling.
- **anytoone-relinking** — `deletePreviousAnyToOneRelations`: stale links deleted via `whereNotIn(inverseJoin, documentSiblingIds)` so other locales/statuses of the same document keep their links.
- **morph-one-cascade-delete** — `deleteRelatedMorphOneRelationsAfterMorphToManyUpdate`: incoming rows whose (type, field) resolves to a morphOne inverse of this relation are grouped by (type, field) into one `$or` DELETE, run before insert in the same transaction; polymorphic identity is always the encoded `${id}:::${__type}` pair.
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
**Data transfer plane**
- **transfer-engine-stage-pipeline** — `TransferEngine.transfer`: fixed stage order schemas→entities→assets→links→configuration with `schemas` never skippable; `only`/`exclude` preset algebra; one `pipeline([source, transform?, tracker?, destination], {signal})` per stage behind a stored AbortController; absent streams are destroyed then `stage::skip` (skip ≠ fail); failure ⇒ diagnostic dedupe + destination-only `rollback(e)` + rethrow.
- **progress-reporting-plane** — `#progressTracker` (per-object count/bytes/aggregates) vs `#progressTrackerChunks` (replaces `asset.stream` with a counting Transform: no double-consumption, backpressure kept, non-Buffer chunk = 1 byte, count in flush); events `transfer::*` + `stage::*` carry the LIVE progress object; source `getStageTotals` merged BEFORE `stage::start` for ETA.
- **remote-push-flow-state-machine** — `createFlow`: `can(step)` = index difference > 0 in the declared Step list, same transfer step may repeat for streaming; `lockTransferStep`/`unlockTransferStep` enforce exactly one locked stage and start-before-end; assets route through per-ID PassThrough registries with sha256 verified before close; writes awaited sequentially.
- **ws-uuid-replay-dispatch** — client resends the byte-identical payload+uuid every 30s (max 5); server checks `hasUUID` BEFORE execution and replays the stored previous response verbatim; response stored on handler state before send; HTTP timeouts + db lifecycles disabled for the connection and restored in the close `finally`; non-matching response frames re-subscribe instead of dropping.
- **asset-chunk-wire-negotiation** — capability negotiated by init ECHO (`assetEncoding:'base64'` returned only if decodable; absent = unsupported); decode ladder accepts base64 string + legacy `{type:'Buffer',data:number[]}` (~6× wire size, #23479) + in-process Buffer; encoders fail fast on null chunks; checksums use the same echo pattern.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
Strapi (`packages/core/database` non-EE portions, MIT Expat; repo carries an EE dual-license split), `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory project `strapi` (FULL mode, generation 2026-08-25T19:58:58Z, 88,379 nodes / 205,881 edges; 55 parse-partial files incl. `database/src/lifecycles/index.ts` range 8-8 and `schema/index.ts` range 11-11 — both verified by direct read; skipped=0). Pass 1 mined the kernel spine (query-builder → entity-manager → lifecycles → relations/populate); pass 2 added the schema-sync plane (`src/schema`) and migration plane (`src/migrations`); pass 3 added the ordering helpers (status sort + deep-sort wrap), the metadata load plane, and the morphOne cascade delete (pass 3 verified by direct source/test read — Codebase Memory MCP was not connected in that session); pass 4 added the data-transfer plane (`packages/core/data-transfer`: engine stage pipeline, progress reporting, remote push flow state machine, uuid dedup-replay dispatch, asset chunk wire negotiation — also verified by direct source/test read at the same pin).

## Full view (memory graph)
Revalidate `strapi` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Recorded pin: root `$REFERENCE_ROOT/strapi`, branch `develop`, HEAD `1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`, mode FULL, nodes 88,379 / edges 205,881. Caveats: `lifecycles/index.ts` is parse-partial at line 8 (type re-export only) and `schema/index.ts` at line 11 (`export type * from './types'` only); `packages/core/types` barrel index files are partially parsed — read flagged ranges directly before citing them.

## Boundaries
Adopt the pure contracts: intent-state→SQL compilation discipline, compensating write rollback, per-subscriber hook state, deterministic identifier compression, batch populate mapping, connect topological ordering, tracked-only schema removals, constraint-safe DDL ordering, exactly-once migration logging with fixed stream order. Adapt transaction scoping, dialect capability flags (`useReturning`, `supportsUnsigned`, postgres type-conversion SQL), reserved-table lists, and metadata shapes to your host ORM/knex version. Omit Strapi-specific product behavior: content-type UIDs, documents service semantics, admin/auth plane, the concrete 5.0.0 internal-migration bodies, EE features.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`alter-table-ladder.md`](./alter-table-ladder.md)
- [`anytoone-relinking.md`](./anytoone-relinking.md)
- [`asset-chunk-wire-negotiation.md`](./asset-chunk-wire-negotiation.md)
- [`batch-populate-apply.md`](./batch-populate-apply.md)
- [`connect-array-orderer.md`](./connect-array-orderer.md)
- [`deep-sort-wrap.md`](./deep-sort-wrap.md)
- [`dual-provider-migrations.md`](./dual-provider-migrations.md)
- [`entity-manager-write-pipeline.md`](./entity-manager-write-pipeline.md)
- [`identifier-shortener.md`](./identifier-shortener.md)
- [`lifecycles-provider.md`](./lifecycles-provider.md)
- [`metadata-load-models.md`](./metadata-load-models.md)
- [`migration-log-storage.md`](./migration-log-storage.md)
- [`migration-runner.md`](./migration-runner.md)
- [`morph-one-cascade-delete.md`](./morph-one-cascade-delete.md)
- [`progress-reporting-plane.md`](./progress-reporting-plane.md)
- [`query-builder-knex-compilation.md`](./query-builder-knex-compilation.md)
- [`relation-shape-builders.md`](./relation-shape-builders.md)
- [`remote-push-flow-state-machine.md`](./remote-push-flow-state-machine.md)
- [`schema-snapshot-storage.md`](./schema-snapshot-storage.md)
- [`schema-sync-gate.md`](./schema-sync-gate.md)
- [`special-type-conversions.md`](./special-type-conversions.md)
- [`status-sort-expression.md`](./status-sort-expression.md)
- [`three-way-schema-diff.md`](./three-way-schema-diff.md)
- [`transfer-engine-stage-pipeline.md`](./transfer-engine-stage-pipeline.md)
- [`ws-uuid-replay-dispatch.md`](./ws-uuid-replay-dispatch.md)
