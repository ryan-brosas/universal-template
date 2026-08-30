<!-- capsule-v2 -->
# datetime-format-offset-suffix — How does DATETIME_FORMAT() render a timestamptz in the viewer's timezone with correct UTC offset text?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What SQL produces pattern formatting PLUS a ±HH:MM offset token?

## TO_CHAR with pattern + computed offset string via epoch-difference ROUND
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:buildTimezoneOffsetSql` (:803-814) + datetimeFormat (:1347-1353); shared helpers in `db-provider/utils/datetime-format.util.ts` (buildDatetimeFormatSql).
**Signature:** `buildTimezoneOffsetSql(localTimestampSql: string): string`; `datetimeFormat(date, format)` passes tzWrap'd expr + offset sql into buildDatetimeFormatSql.
**Data Shape:** offset = `(CASE WHEN mins >= 0 THEN '+' ELSE '-' END || LPAD(ABS(mins)/60,2,'0') || ':' || LPAD(ABS(mins)%60,2,'0'))` where mins = ROUND(EPOCH((x AT TZ 'UTC') - (x AT TZ '<tz>'))/60).

### Decisive source
```ts
const offsetMinutesSql = `ROUND(EXTRACT(EPOCH FROM (
  ((${local}) AT TIME ZONE 'UTC') - ((${local}) AT TIME ZONE '${safeTz}')
)) / 60)::int`;
```

**Flow:** operand → tzWrap (sanitize/trust ladder) → pattern built from field formatting presets (US/European/Asian/Y/M/D + 12/24h) → TO_CHAR renders local wall time → offset expression appended for tokens needing it → shared util assembles final string.
**Invariant:** the offset derives from the SAME tz-wrapped local timestamp by diffing its UTC vs tz renderings — computing it from NOW or session state would desynchronize from the formatted value. TZ strings quote-doubled; preset switch normalizes unknown presets to ISO.
**Probe:** upstream direct spec pins the parse-side twin (`select-query.postgres.spec.ts:29-46` expects `AT TIME ZONE 'Asia/Shanghai'` in DATETIME_PARSE output); static byte-exact: `grep -n "AT TIME ZONE 'UTC') - " select-query.postgres.ts` → :810 region.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"buildDatetimeFormatSql","limit":5,"detail":"ids"}'
```

## Verdict
Adopt derive-offset-from-the-same-expression. Adapt preset table. Omit nothing.
