<!-- capsule-v2 -->
# datetime-sanitize-tzwrap — When is a datetime operand sanitized through the default parse pattern, and when trusted?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What gate decides BTRIM+regex sanitization vs direct ::timestamptz cast?

## tzWrap: sanitize unless (metadata-trusted OR already timestampish); tz always quoted-escaped
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/select-query/postgres/select-query.postgres.ts:tzWrap` (:784-801) + `sanitizeTimestampInput` (:734-739) + trust probes `isTrustedDatetime` (:740-754)/`isTimestampish` (:755-764).
**Signature:** `private tzWrap(date: string, metadataIndex?: number): string`.
**Data Shape:** sanitized form = `CASE WHEN NULLIF(BTRIM(x::text),'') IS NULL … WHEN LOWER(x) IN ('null','undefined') THEN NULL WHEN x ~ '<defaultPattern>' THEN x ELSE NULL END`; with context timeZone → `<base>::timestamptz AT TIME ZONE '<tz>'`, without → `::timestamp`.

### Decisive source
```ts
const trusted = shouldTreat && this.isTrustedDatetime(date, metadataIndex);
const alreadyTimestamp = !isTextLike && this.isTimestampish(date);
const needsSanitize = !(trusted || alreadyTimestamp);
const baseExpr = needsSanitize ? this.sanitizeTimestampInput(date) : `(${date})`;
...
const safeTz = tz.replace(/'/g, "''");
return `${wrappedBase}::timestamptz AT TIME ZONE '${safeTz}'`;
```

**Flow:** metadata says the slot is a real date field and not json/multi → TRUSTED (no sanitize, no re-parse) → expression already carries ::timestamp/AT TIME ZONE/NOW() markers → treated as timestamp (skip) → otherwise full sanitize ladder (trims, nulls 'null'/'undefined' strings, regex-guards against the shared default pattern) → wrap to timestamptz in session tz.
**Invariant:** sanitization is keyed on METADATA trust, never on string shape alone — a CONCAT that happens to contain a timestamp token is NOT trusted (`shouldTreatAsDatetime` returns false for number/boolean-typed metadata even when tokens match). TZ strings are always quote-doubled before inlining.
**Probe:** upstream direct spec `select-query.postgres.spec.ts:9-46` pins BOTH polarities (text-like input gains BTRIM/CASE/default-pattern; trusted datetime input does NOT; custom-format reparse goes through TO_CHAR/TO_TIMESTAMP AT TIME ZONE).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"tzWrap","limit":3,"detail":"ids"}'
```

## Verdict
Adopt trust-ladder + sanitize CASE + quote-escaped AT TIME ZONE wrapping. Adapt default pattern constant. Omit nothing.
