<!-- capsule-v2 -->
# credit-hold scope migration — when does a globally-unique reservation key become a cross-tenant hazard?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What schema change turns an incidental caller convention ("everyone namespaces their refs") into an enforced invariant?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/meta/migrations/v0/nc_202608191200_credit_hold_ref_scoped.ts` (whole, 27L).
**Signature:** standard knex `up/down` pair on MetaTable.CREDIT_HOLDS.
**Data Shape:** unique index moves `['request_ref']` → `['scope','fk_scope_id','request_ref']`.

### Decisive source
```sql
-- docstring:
-- `request_ref` was globally unique — one namespace shared by every tenant. A
-- ref another scope already held would fail to insert (and `hold` swallows
-- that as "already held", running the call unreserved), while an unscoped
-- deleteByRequestRef could release the wrong tenant's hold. Safe today only
-- because every caller happens to namespace its refs; this makes it schema.
table.dropUnique(['request_ref']);
table.unique(['scope', 'fk_scope_id', 'request_ref']);
```

**Flow:** up drops the global unique and recreates it scoped by (scope, fk_scope_id, request_ref); down reverses exactly.
**Invariant:** (1) Two failure modes of a global key: a foreign-scope collision makes `hold` silently run UNRESERVED (swallowed as already-held), and unscoped release can drop ANOTHER tenant's hold — both fixed by one composite unique. (2) Convention→schema: if safety depends on every caller prefixing keys correctly, move that requirement into the constraint. (3) Down must mirror precisely or rollback leaves tenants unable to collide-safe-reserve.
**Probe:** `sed -n '1,27p' packages/nocodb/src/meta/migrations/v0/nc_202608191200_credit_hold_ref_scoped.ts` whole file read this session; registered in XcMigrationSourcev0.ts import + name lists (:95/:199/:397). No unit runner for v0 migrations (standing caveat).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "credit hold request_ref scoped unique migration", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the convention→constraint principle + composite-key shape; adapt table/scope column names; omit EE credit system itself (product surface).
