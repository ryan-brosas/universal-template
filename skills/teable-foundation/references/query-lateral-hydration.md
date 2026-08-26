<!-- capsule-v2 -->
# Lateral-join table hydration — how does one SELECT load a table with ordered fields and views while honoring soft-delete state?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Why does field order come from an is_primary-first sort, and how do deleted-child rules differ between active and deleted queries?

## selectNoFrom + jsonArrayFrom laterals + primary-field ordering contract
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/PostgresTableRepository.ts`: `findOne` (:583-728) / `find` (:731-853) shared lateral assembly (:626-707 / :747-825), ordering clause (:655-661 with the API-compatibility comment), deleted-child branching (:662-668 active vs :664-668 deleted-equality), spec→where via TableWhereVisitor + span attributes from `visitor.describe()` (:595-621).
**Signature:** `orderBy(sql`${sql.ref('is_primary')} is null`, 'asc').orderBy('is_primary').orderBy('order').orderBy('created_time')`.
**Data Shape:** effectiveState default 'active'; 'deleted' matches children whose deleted_time EQUALS the table's (paired tombstones); not-found errors embed the SPEC description (`formatSpecDetails` :25-36) for debuggability.

### Decisive source
```ts
// Keep the hydrated field array aligned with the existing field list API.
// Selection range column indexes depend on this fallback order when the
// view has no explicit columnMeta.order entries.
.orderBy(sql`${sql.ref('is_primary')} is null`, 'asc')   // primary first (NULLS LAST inverse)
.orderBy('is_primary')
.orderBy('order')
.orderBy('created_time');
```

**Flow:** visitor turns the specification into a where-factory (+ span attrs: table_spec, base_id, table_ids…) → two selectNoFrom laterals aggregate fields/views as JSON arrays correlated by table_meta.id → leftJoinLateral(onTrue) → optional sort/pagination for find() → rows mapped through mapTableRow → mapper.toDomain. Deleted state swaps child filtering from IS NULL to timestamp EQUALITY so a deleted query returns the exact historical child set.
**Invariant:** Field array ORDER is a wire contract (grid selection ranges index into it) — reordering these ORDER BY terms silently corrupts clients that rely on fallback ordering when columnMeta.order is absent. Laterals keep it one round trip without N+1; empty children arrive as [] not NULL.
**Probe:** `PostgresTableRepository.spec.ts` findOne/find suites; ordering contract documented in-source at :655-657.
**Coverage caveat:** mapping covered by helpers spec; lateral SQL shape itself verified by source + integration specs elsewhere.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRepository findOne jsonArrayFrom leftJoinLateral shouldFilterDeletedChildren", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt lateral hydration + the primary-first ordering contract (treat the comment as a spec); adapt state vocabulary; preserve paired-tombstone equality for deleted reads.
