<!-- capsule-v2 -->
# Import sanitize + alias — how do imported column names survive DB constraints while keeping their display titles distinct?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Why does the importer track title-alias separately from column_name during Airtable import?

## dual-track naming: sanitized column_name vs unique title
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts:nc_getSanitizedColumnName/addFieldAlias/getNcFieldAlias` (249-259, 397-411).
**Signature:** `nc_getSanitizedColumnName(name, table_name): {title, column_name}`; `addFieldAlias(ncTableTitle, atFieldAlias, ncFieldAlias): void`.
**Data Shape:** `column_name` = `sanitizeColumnName(name, dbType).slice(0, 50)` then uniquified per table ('column' prefix gen); `title` = name with dots replaced, uniquified per table ('field' prefix gen).

### Decisive source
```ts
const nc_getSanitizedColumnName = (name, table_name) => {
  const uniqueColNameGen = getUniqueNameGenerator('column', table_name);
  const uniqueFieldNameGen = getUniqueNameGenerator('field', table_name);

  // truncate to 50 chars if character if exceeds above 50
  const col_name = sanitizeColumnName(name, getRootDbType())?.slice(0, 50);

  // for knex, replace . with _
  const col_alias = name.trim().replace(/\./g, '_');

  return { title: uniqueFieldNameGen(col_alias), column_name: uniqueColNameGen(col_name) };
};
```

**Flow:** every created column gets BOTH a DB-safe physical name and a display title; the field-alias registry (`atFieldAliasRef[tableTitle][atFieldAlias] → ncFieldAlias`) lets later phases translate Airtable field references (formulas, lookups, sort/filter configs) into NocoDB titles without touching the physical names.
**Invariant:** sanitization and truncation apply to column_name ONLY — titles keep user-visible text (minus dot hazards). Uniqueness generators are TABLE-SCOPED, so two tables can each have a `Name` column. Alias registration must happen at creation time; formula rewriting later depends on it.
**Probe:** no unit test upstream. Source-grounded probe: `at-import.processor.ts:397-411` — dual generator construction; `:62-107` selectColors table shows the parallel concern for select-option display fidelity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "nc_getSanitizedColumnName addFieldAlias getUniqueNameGenerator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-track naming with table-scoped uniqueness and an alias registry for expression rewrite; adapt sanitize rules/truncation to your DB; omit color-palette preservation unless porting select options too. Coverage caveat: no in-repo tests; source-grounded.
