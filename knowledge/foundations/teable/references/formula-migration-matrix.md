<!-- capsule-v2 -->
# Formula→any migration matrix — how are formula CELL VALUES (not expressions) carried across a type conversion, and when is nulling the contract?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** For each (formula cellValueType → target field type) pair, what UPDATE expression preserves or intentionally discards data?

## buildFormulaMigrationSql
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldTypeConversionVisitor.ts` — `buildFormulaMigrationSql` (:1131–1237); wrapper `buildFormulaMigrationStatements` (:934–1012); format translator `dayjsFormatToPostgres` (:882–900) + `buildPgDateTimeFormat` (:909–920).
**Signature:** `(tbl, dst, tmp, whereNotNull, cellValueType, newType, oldField, params): string | null` — null ⇒ incompatible pair, values become NULL by design.
**Data Shape:** source types: number(`double precision`)/dateTime(`timestamptz`)/boolean/string; targets: singleLineText|longText, number, rating, date, checkbox, singleSelect, multipleSelect.

### Decisive source
```sql
-- dateTime → text honors the FORMULA'S display formatting via to_char:
UPDATE tbl SET dst = to_char(tmp AT TIME ZONE 'TZ', 'pgFormat') WHERE tmp IS NOT NULL;
-- string → number: regex-guarded cast, non-numeric ⇒ NULL
UPDATE tbl SET dst = CASE WHEN tmp ~ '^-?[0-9]+(\.[0-9]+)?$'
                          THEN tmp::double precision ELSE NULL END WHERE tmp IS NOT NULL;
-- any → checkbox mirrors v1 truthiness: ANY non-null value becomes TRUE
UPDATE tbl SET dst = TRUE WHERE tmp IS NOT NULL;
```

**Flow:** rename column → drop old schema (forConversion: keep outbound refs) → create target schema → optional options-minting for select targets → run matrix UPDATE against the temp column → drop temp. Number→rating clamps to `[1,max]`; boolean→date/number returns null (incompatible); dateTime formatting uses dayjs-token→PG to_char translation with timezone AT TIME ZONE shift BEFORE formatting.
**Invariant:** NULL return ≠ error — it encodes v1's 'incompatible conversions produce empty cells' semantics, so porters must not throw on unsupported pairs; every UPDATE is guarded by `WHERE tmp IS NOT NULL`.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/__tests__/FieldTypeConversionVisitor.spec.ts` SQL-snapshot pins :311 'parse ISO date strings', :325 'require the whole text value to be an ISO date before casting'; pglite behavioral specs under Edge cases (:390).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildFormulaMigrationSql dayjsFormatToPostgres buildPgDateTimeFormat ISO_DATE_OR_DATETIME_SQL_REGEX", limit: 10 });
```

## Verdict
Adopt the typed migration matrix with explicit null-for-incompatible contract and regex-guarded casts; adapt type pairs/format tokens to host field model; omit v1-truthiness quirks if host defines its own conversion semantics.
