<!-- capsule-v2 -->
|# Keyset backfill walk — id-cursor batching, join hydration, and the random-id creation bound

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What is nocodb's canonical shape for a migration touching a potentially huge meta table without loading it or re-walking rows?

## Path/Symbol
`packages/nocodb/src/modules/jobs/migration-jobs/nc_job_015_pg_source_searchpath_backfill.ts:job` loop (147–226; BATCH_SIZE :74; candidate filter 110–129).

**Signature:** `while (true) { rows = qb.where(id > lastId).orderBy(id asc).limit(N).join(...); if (!rows.length) break; lastId = rows.at(-1).id; ... }`.

**Data Shape:** one LEFT JOIN per page pulls the inherited-config column (`integrations.config as integration_config`) beside `sources.*`, so each row hydrates into a full in-memory model (`new Source(row)`) whose merged getters work with zero extra queries. Count query reuses the SAME filter builder for consistent totals.

### Decisive source
```ts
// Read the candidate set in keyset-paginated pages. Loading every row up
// front is an unbounded memory load on instances with many (10k+) external
// sources, so we page by `id` and process each page before fetching the next.
// Keyset (`id > lastId`) — not OFFSET — keeps every page a flat index scan
// instead of re-walking all skipped rows.
.where(`${SOURCES}.id`, '>', lastId)
.orderBy(`${SOURCES}.id`, 'asc')
.limit(BATCH_SIZE)
```

**Flow:** count (same filter) → page loop → per-row try/catch (log + continue) → progress log per page (`evaluated/total, pinned so far`). Creation-race guard: `created_at < startedAt` in the filter because nanoid ids are NOT time-ordered — a source created mid-run can land in an unvisited page and must be excluded from mutation.

**Invariant:** (1) Cursor = last row's id under monotone ORDER BY — immune to insert/delete churn between pages where OFFSET drifts or duplicates. (2) Join-hydration per page beats N+1 model gets while preserving getters. (3) The startedAt bound is REQUIRED only because ids are random; sequential ids make keyset alone safe. (4) Termination = empty page, never a row-count target.

**Probe:** no unit test upstream. Source-grounded probe: nc_job_015:69-74 (keyset-vs-offset comment), :79-93 (creation-window), :148-152 (single-join hydration), :172-221 (per-row isolation). Contrast: offset-under-PQueue paging in migration-trash-backfill.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "BATCH_SIZE lastId applyCandidateFilter orderBy id asc", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt id-keyset paging, join-hydration per page, and the random-id creation bound; adapt filters; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
