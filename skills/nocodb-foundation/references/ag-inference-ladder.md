<!-- capsule-v2 -->
# AG inference ladder — when must a primary key be treated as NocoDB-generated rather than DB-provided?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** During introspection, under what conditions is a PK tagged auto-generated (`meta.ag = 'nc'`), and why does the mssql arm need a third guard?

## AG inference ladder
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — databricks arm (:453–459), mssql arm (:461–471) inside the per-column insert loop.
**Signature:** inline: `if (column.pk && !column.cdf)` (databricks); `if (column.pk && !column.cdf && !column.ai)` (mssql) → `column.meta = { ag: 'nc' }`.
**Data Shape:** `cdf` = column has a DB default; `ai` = auto-increment/IDENTITY flag from columnList.

### Decisive source
```ts
// :461–471 (verbatim incl. the incident comment):
// MSSQL: a PK that is neither IDENTITY (auto-increment → AI) nor backed
// by a DB default (e.g. NEWID()) must be NocoDB-generated (AG). Identity
// columns report no column_default, so the !ai guard is required to
// avoid mis-tagging them as AG.
if (source.type === 'mssql') {
  if (column.pk && !column.cdf && !column.ai) {
    column.meta = {
      ag: 'nc',
    };
  }
}
```

**Flow:** for each physical column of each table → dialect check → PK without default and (mssql) without identity ⇒ NocoDB will generate values client-side, so stamp `meta.ag='nc'`; otherwise leave meta untouched.
**Invariant:** The mssql predicate is THREE-way. Identity columns on MSSQL report no `column_default`, so testing only `pk && !cdf` would mis-tag every IDENTITY table as NocoDB-generated and NocoDB would then try to supply its own ids, colliding with SQL Server's sequence. Databricks keeps the two-way test because it lacks the IDENTITY reporting quirk in this codepath.
**Probe:** `grep -c "ag: 'nc'" packages/nocodb/src/helpers/populateMeta.ts` → `2`.
**Coverage caveat:** grep-derived; no direct unit spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "populateMeta ag nc cdf ai", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-guard mssql rule and its rationale comment verbatim; adapt dialect names to host; omit the bytea-format colMeta merge at insert time (:481).
