<!-- capsule-v2 -->
# Import column mapping — how are source columns bound to destination fields when the user may create new columns, rename, or link mid-import?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does explicit columnMapping resolve destinations, and why is create-column skipping keyed on TITLE not column_name?

## classifyDest + title-keyed create dedup
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:importSheet` mapping block (418-481), `createMappedColumns` (562-639).
**Signature:** `classifyDest(srcColName, dest, delimiter?)` → fills `colMap` (scalars) vs `ltarColMap` (links); `createMappedColumns(...): Promise<Map<sourceCn, ColumnType>>`.
**Data Shape:** mapping row `{sourceCn, destCn, enabled, createColumn, linkConfig?: {delimiter}}`; resolution order for createColumn: created-map → existing-by-TITLE.

### Decisive source
```ts
// For a "create new field" row, map to the column we actually created
// (resolved by id). If creation was skipped because the title matched an
// existing field, fall back to that existing column by TITLE only —
// never by column_name, so a name-only clash can't silently reroute the
// imported data into an unrelated existing column.
const dest = m.createColumn
  ? createdColumns.get(m.sourceCn) ?? tableColumns.find((c) => c.title === m.destCn)
  : findDest(m.destCn);
...
const takenTitles = new Set(existing titles);   // skip-on-title only
if (!title || takenTitles.has(title)) continue; // treat as "map to that field"
// per-column failure: skip, don't abort
} catch (e) { log(`Failed to create field "${title}"... Skipping this field.`); }
```

**Flow:** enabled mappings resolve to destination columns; LTAR targets split into a separate map whose cells hold display values handled post-insert. Requested new columns are added first (inheriting source type, text default), then columns refresh and mapping resolves against reality — a create request colliding with an existing title silently maps instead of duplicating.
**Invariant:** never fall back to `column_name` matching for created-column rows: `columnAdd` dedupes generated column_names, so a name-only match could reroute imported data into an unrelated physical column. One failed `columnAdd` skips that field; it must not fail the import. Zero resolvable mappings overall IS a hard error (`NcError.badRequest`).
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:454-465` — the title-only fallback with its explanatory comment; `:614-623` — catch-log-continue in createMappedColumns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "classifyDest createMappedColumns columnMapping ltarColMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scalar/link destination splitting, title-keyed create-dedup, and per-field failure isolation; adapt mapping schema to your import UI; omit dtxp/meta passthrough unless porting NocoDB column metas. Coverage caveat: no in-repo tests; source-grounded.
