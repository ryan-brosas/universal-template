<!-- capsule-v2 -->
|# pg type-cast SQL composers — how do text columns become Number/Date/Duration/etc. in pure SQL, and why does every composer end in NULL instead of error?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does generateCastQuery emit per UITypes, and what are the extractNumber/bounding/datetime-composition contracts?

## pg type-cast SQL composers
**Path/Symbol:** `packages/nocodb/src/db/sql-client/lib/pg/typeCast.ts` — `extractNumberQuery` (:14–40), `generateBooleanCastQuery` (:48–56), `generateDateTimeCastQuery` (:67–95), `generateNumberBoundingQuery` (:105–119), `generateToDurationQuery` (:134–152), `getDateFormat` (:154–166), `generateCastQuery` (:188–239), `formatColumn` (:248–271); regex tables `pg/constants.ts:DATE_FORMATS/TIME_FORMATS`; sole caller PgClient.alterTableColumn :3303–3317.
**Signature:** `generateCastQuery({uidt, dt, source, limit, format, durationType=0}): string` — pure string composition, NO knex, NO binding.
**Data Shape:** `source` is an already-formatted SQL expression (formatColumn output); returns one statement ending `;`.

### Decisive source
```sql
-- extractNumberQuery :16–39 — sentinel-swap laundering (each step load-bearing):
CAST(NULLIF(REPLACE(REPLACE(REPLACE(
  REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(src,'[^0-9.-]','','g'),
    '^-','~'),            -- 1. protect ONE leading sign
    '-',''),              -- 2. strip remaining '-' INSIDE the string (ranges "10-20"→"1020")
  '(\d)\.(\d)','\1-\2'),  -- 3. FIRST decimal point becomes '-'
  '.',''),                -- 4. later decimal points deleted ("1.2.3"→"12-3")
'-','.'),'~','-'), '') AS DECIMAL)   -- 5. swap back; '~'→'-' restores the sign
-- NULLIF(x,'') → empty-after-strip renders NULL, never a cast error.
```
```ts
// generateNumberBoundingQuery :110–118 — out-of-band sentinels:
NULLIF(NULLIF(LEAST(${max+1}, GREATEST(${min-1}, x)), ${min-1}), ${max+1})
// Year: bounds 1000..9999 — a legit year can never equal min-1/max+1, so clamp-and-null is lossless.

// generateDateTimeCastQuery :75–94 — CASE × CASE over DATE_FORMATS[k] × TIME_FORMATS,
// combined regex = dateRegex minus '$' + '\\s+' + timeRegex minus '^'; each hit calls
// to_date_time_safe(source,'FORMAT') — a DB-side helper that must pre-exist;
// dateFormat==='empty' (Time uidt) adds ['', '^$'] so bare times parse; unknown format ⇒ badRequest.

// generateToDurationQuery :142–151 — format-id semantics: 0=h:mm (single number=MINUTES ×60),
// 1–4=m:s (single number=SECONDS); 3-part always h*3600+m*60+s; day formats fall to numeric extraction.
```
Dispatch (:196–238): text family → `::VARCHAR(limit||255)`; LongText → `::TEXT`; Number → CAST(extract AS BIGINT); Year → bounding(1000,9999); Decimal/Currency → bare extract; Percent → LEAST(100,GREATEST(0,…)); Rating → LEAST(limit||5,GREATEST(0,…)); Checkbox → LOWER-IN truthy/falsey token sets ('[x]','☑','✅','✓','✔','on','done',… vs '[]','[ ]','off',…); Date/DateTime/Time → datetime CASE; Duration → duration CASE; default → `null::${dt}`.

**Flow:** ALTER TYPE ... USING needs one expression converting arbitrary existing cell text into the new type without failing the whole migration → formatColumn first normalizes the OLD column to comparable text (numeric families CAST AS VARCHAR(255), checkbox → '1'/'0' CASE) → generateCastQuery wraps it per target uidt → embedded after `TYPE ${dt} USING `. Everything composes as TEXT because these run inside genQuery with shouldSanitize=true.

**Invariant:** (1) Composers are total functions on cell data: every path ends ELSE NULL / NULLIF-empty / bounding-null — a single poison row aborting ALTER TABLE is the bug this file exists to prevent. (2) The extractNumber sentinel order is exact: leading-sign protection must precede inner-dash stripping, and only the FIRST dot becomes the decimal — reorder and "-1.2-3" class inputs corrupt silently. (3) Bounding uses min−1/max+1 SENTINELS not clamping: values outside domain become NULL (unknown), never silently clipped to the boundary. (4) `to_date_time_safe` is an EXTERNAL dependency — the cast fails at runtime unless that helper was installed (dateConversionFunction plumbing). (5) formatColumn vs generateCastQuery are two halves of one round-trip: casting without formatting first mis-parses numeric-stored-as-other-type cells.

**Probe:** runner BLOCKED (no upstream unit spec imports typeCast — grep across src/**/*.spec.ts = 0) → deterministic probes at pin: `sed -n '105,119p' packages/nocodb/src/db/sql-client/lib/pg/typeCast.ts` shows the nested NULLIF verbatim; `grep -c "to_date_time_safe" packages/nocodb/src/db/sql-client/lib/pg/typeCast.ts` = 1 (single emission site); `grep -n "durationType === 0" packages/nocodb/src/db/sql-client/lib/pg/typeCast.ts` pins the h:mm fork :135.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "generateCastQuery extractNumberQuery generateToDurationQuery formatColumn", limit: 10 });
```

## Verdict
Adopt the total-function cast discipline (NULL on unparseable, sentinel bounding, token-set booleans), the format-id duration semantics, and the format-then-cast pairing; adapt regexes/token sets to host locales; omit to_date_time_safe's body (external helper — install or replace with host equivalent).
