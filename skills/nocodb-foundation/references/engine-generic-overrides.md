<!-- capsule-v2 -->
# PG/MySQL/SQLite generic overrides — how does each engine's generic subclass change contains-matching and membership ops?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What exactly do GenericPgFieldHandler, GenericMysqlFieldHandler, and GenericSqliteFieldHandler override, and what incident does the PG nlike comment record?

## Engine generic subclasses
**Path/Symbol:** `generic.pg.ts` — filterLike :19-58 (::text ilike; ref-path keeps pattern binding); filterNlike :60-114; innerFilterAllAnyOf :116-174 (`(',' || ??::text || ',') ilike ?` pairs + enum/set trimEnd). `generic.mysql.ts` (:10-64) CONCAT-based anyof with trimEnd on enum/set dt. `generic.sqlite.ts` (:11-63) `||`-concat like twin.
**Signature:** all three extend GenericFieldHandler implementing FilterOperationHandlers; registry wires MultiSelect/SingleSelect (PG→pg, MYSQL→mysql-multi, SQLITE→sqlite) plus LongText-PG delegation.
**Data Shape:** trimEnd applies ONLY when `['enum','set'].includes(column.dt?.toLowerCase())` — MySQL enum labels may carry trailing spaces in DDL.

### Decisive source
```ts
// generic.pg.ts :76-83 — the recorded regression:
// if value is not empty, empty or null should be included.
// The legacy conditionV2 path emitted `orWhere(field, '')` here —
// restore that. The previous `??::text != ''` had the comparison
// operator flipped, matching nearly every row and breaking
// Filter `nlike` parity on PG for SingleSelect/MultiSelect.
qb.orWhere(knex.raw(`??::text = ''`, [sourceField]));
qb.orWhereNull(sourceField as any);
```

**Flow:** PG: every text comparison coerces ::text first so select-typed columns compare as strings; ilike replaces like; the ref-path of LIKE binds the pattern raw instead of interpolating. MySQL/SQLite: only the membership family is overridden (CONCAT vs || concatenation), inheriting generic eq/neq/likes unchanged. Negated membership = whereNot(condition) + orWhereNull in ALL three.
**Invariant:** (1) The PG nlike flip comment is a regression headstone: `!= ''` matched nearly EVERY row because non-empty strings satisfy it — the correct arm re-admits empty strings via `= ''`. (2) enum/set trimEnd must NOT apply to plain text columns (trailing spaces are significant there). (3) PG's ilike choice makes its semantics MATCH the other engines rather than SQL-standard LIKE — parity beats standardness here.
**Probe:** No unit tests upstream at pin. Deterministic probe: grep "matching nearly every row" (:81); search_graph resolves `GenericPgFieldHandler.filterNlike Method ... generic.pg.ts 51-95` line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "GenericPgFieldHandler", limit: 5 });
```

## Verdict
Adopt per-engine override scope (PG broad, MySQL/SQLite narrow); adapt coercion syntax; preserve the empty-string-re-admission rule verbatim. Caveat: no direct tests at pin.
