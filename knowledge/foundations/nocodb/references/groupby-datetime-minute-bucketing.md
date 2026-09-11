<!-- capsule-v2 -->
# Datetime minute-bucket group keys — five engines, one truncation semantics, TZ-normalized on Oracle

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How are DateTime/CreatedTime/LastModifiedTime keys truncated so groups align with the UI and stay identical between list() and count()?

## Per-dialect minute-truncation table
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts` list branch :259-320; count twin :865-953.
**Signature:** same selector pushed in both functions — the pair MUST stay in lockstep (source comments say so explicitly).
**Data Shape:** key expression per dialect, aliased via `getAs(column)`.

### Decisive source
```sql
-- pg (:267-271): truncate + no-op add keeps the TIMESTAMP type:
date_trunc('minute', col) + interval '0 seconds'

-- mysql (:272-279): convert to UTC THEN strip seconds — order matters,
-- otherwise buckets split across session-TZ boundaries:
DATE_SUB(CONVERT_TZ(col, @@GLOBAL.time_zone, '+00:00'), INTERVAL SECOND(col) SECOND)

-- sqlite list (:280-284): strftime to whole minutes...
strftime('%Y-%m-%d %H:%M:00', col)
-- ...but count (:892-913) APPENDS an offset suffix by re-parsing chars 20+ of
-- the stored string ('+'/'-' branches rebuilding '+HH:' 'MM', ELSE '+00:00') —
-- count keys carry the offset so totals match rows grouped under any offset.

-- mssql (:285-295): VERSION-gated — 2022+ has native DATETRUNC;
-- older must round-trip style-120 text, VARCHAR(16) dropping the seconds:
major >= 16 ? DATETRUNC(MINUTE, ??) : CONVERT(DATETIME, CONVERT(VARCHAR(16), ??, 120))

-- oracle (:296-310): NO DATE() function (ORA-00904); TRUNC a DATE cast.
-- TIMESTAMP WITH [LOCAL] TIME ZONE columns FIRST normalize SYS_EXTRACT_UTC —
// plain TIMESTAMP must NOT get it (ORA-30175) since it already stores UTC
// wall time. isWithTimeZone = dt contains 'time zone' (:49-50).
TRUNC(CAST([SYS_EXTRACT_UTC(]col[)] AS DATE), 'MI')
```

**Flow:** resolve physical column name → pick dialect expression → alias → push into selectors AND groupBySelectors (both functions).
**Invariant:** (1) The list/count expressions are deliberately near-duplicates; changing one without the other makes group totals disagree with group contents. (2) Oracle's SYS_EXTRACT_UTC gate is keyed on the COLUMN's physical dt, not the UI type. (3) MySQL converts before stripping seconds — reversing produces different bucket membership for cross-TZ data.
**Probe:** No unit tests upstream. Deterministic probe: rendering both paths for one pg datetime column yields identical `date_trunc('minute'...)` text in list and count SQL.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "date_trunc minute groupBy", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (datetime branch :259-320)
```

## Verdict
Adopt the five-way truncation table incl. the SQLite count-only offset suffix and Oracle TZ gate. Adapt version sniffing to host metadata source. Caveat: no direct tests at pin; graph ranges verified live.
