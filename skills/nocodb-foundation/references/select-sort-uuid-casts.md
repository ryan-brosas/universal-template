<!-- capsule-v2 -->
# Select sort dialects + UUID casts — why must MySQL select sorts CONCAT() and PG uuid comparisons cast to text?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Which column families need a sort-expression rewrite per engine, and how does UUID filtering avoid "invalid input syntax for type uuid"?

## MultiSelect applySort + UuidPgHandler
**Path/Symbol:** `multi-select/multi-select.general.handler.ts` applySort :25-45 (MySQL `CONCAT(??)` wrap :40; comment :21: sorting native enum orders by declared option POSITION, users expect label order). `multi-select.mysql.handler.ts` (:16-26) same CONCAT wrap on the MySQL-registry class. `uuid/uuid.pg.handler.ts` (300L) — every op re-binds as `??::text` (filterEq :21-47).
**Signature:** `UuidPgHandler extends GenericPgFieldHandler implements FilterOperationHandlers` — overrides eq/neq/blank/notblank/gt/gte/lt/lte/like/nlike with `::text` casts.
**Data Shape:** Registry wiring: MultiSelect/SingleSelect on PG → GenericPgFieldHandler (ilike family); on MySQL → MultiSelectMysqlHandler; UUID on PG/MSSQL → dedicated handlers, else generic.

### Decisive source
```ts
// multi-select.general.handler.ts :31-35:
// Single/MultiSelect ORDER BY in MySQL needs `CONCAT(col)` to coerce the
// underlying `enum`/`set` type into a string — sorting on the native
// `enum` orders by the declared option position, not the option label.
// uuid.pg.handler.ts :10-13:
// PostgreSQL UUID field handler that casts UUID to text for all comparisons.
// This allows filtering with partial text values without PostgreSQL throwing
// "invalid input syntax for type uuid" errors.
```

**Flow:** sort path — MySQL registry entry wraps the column in CONCAT so ORDER BY sees the label string; other engines keep the bare column. Filter path — partial-UUID LIKE/prefix filters would make PG parse the fragment AS UUID and throw; casting both sides to ::text downgrades every comparison to string semantics (including range ops).
**Invariant:** (1) The enum-position trap is silent: without CONCAT the query SUCCEEDS but returns wrong order — a porting miss that no test error will surface. (2) ::text casts sacrifice index usage for correctness; upstream accepts this because UUID prefix search is rare. (3) MSSQL has a UUID handler registered but its class body is empty at this pin — the cast work lives only in PG's.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "orders by the declared option position" (:32-34); search_graph resolves `UuidPgHandler.filterEq Method ... uuid.pg.handler.ts 21-48` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "UuidPgHandler", limit: 5 });
```

## Verdict
Adopt the sort-coercion wrap and full-cast UUID policy; adapt enum/set detection (`column.dt`) to your schema; omit empty shells. Caveat: no direct tests at pin.
