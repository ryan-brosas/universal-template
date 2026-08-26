<!-- capsule-v2 -->
# column-name sanitize + alias resolution — when does a physical column keep its raw name and how do system time/user twins resolve?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How are user-supplied column names sanitized for DDL, and how does `getRefColumnIfAlias` map alias columns (CreatedTime etc.) back to their hidden system twins?

## column-name sanitize + alias resolution
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `sanitizeColumnName` (:673–695), `getRefColumnIfAlias` (:699–723), `deleteColumnSystemPropsFromRequest` (:842–882).
**Signature:** `sanitizeColumnName(name: string, sourceType?: DriverClient) → string`; `getRefColumnIfAlias(context, column, columns?) → Promise<Column | null>`.
**Data Shape:** sanitization regex builds from SDK constants `REGEXSTR_INTL_LETTER` + `REGEXSTR_NUMERIC_ARABIC` (international letters, arabic numerals) + `_`; everything else → `_`.

### Decisive source
```ts
// :673–691:
export const sanitizeColumnName = (name: string, sourceType?: DriverClient) => {
  if (
    process.env.NC_DATABASE_COLUMN_NAME_SANITIZE_ENABLED === 'false' ||
    process.env.NC_SANITIZE_COLUMN_NAME === 'false'
  )
    return name;
  let columnName = name.replace(
    new RegExp(`[^${REGEXSTR_INTL_LETTER}${REGEXSTR_NUMERIC_ARABIC}_]`, 'g'),
    '_',
  );
  // if column name only contains _ then return as 'field'
  if (/^_+$/.test(columnName)) columnName = 'field';
  if (sourceType) {
    if (sourceType === DriverClient.DATABRICKS) {
      // databricks column name should be lowercase
      columnName = columnName.toLowerCase();
    }
  }
  return columnName;
};
```

**Flow:** two env kill-switches (legacy + current name) disable sanitization entirely → non-[intl-letter/numeric/_] runs collapse to `_` → all-underscore names become literal `field` → databricks lowercases. ALIAS RESOLUTION: only four uidts qualify (CreatedTime, LastModifiedTime, CreatedBy, LastModifiedBy) → search provided list or reload model columns for a SYSTEM column with the SAME uidt → fall back to input. REQUEST STRIPPING: `deleteColumnSystemPropsFromRequest` deletes 13 physical-DDL props (`dt,np,ns,clen,cop,pk,rqd,un,ai,cc,csn,dtx,au,validate` — note dtxs/scale deliberately kept) then switches on OperationSource: AT_IMPORT keeps `system` only for ncRecordId/ncRecordHash titles; SYNC keeps caller's `system` ("table-sync flags its Remote*/Sync* metadata columns as system so they hide behind 'Show system fields'"); default strips it.
**Invariant:** Sanitization is opt-OUT (default on) and preserves international letters — ASCII-only assumptions corrupt non-Latin schemas. Alias resolution must match on uidt EQUALITY plus system flag; matching by title would miss localized aliases.
**Probe:** `grep -c "NC_DATABASE_COLUMN_NAME_SANITIZE_ENABLED" packages/nocodb/src/helpers/columnHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "sanitizeColumnName getRefColumnIfAlias", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt opt-out sanitization with intl-letter classes, `field` fallback, databricks lowercase; adopt per-operation-source system-stripping matrix exactly (import keeps ncRecord* titles, sync honors flags); adapt env names.
