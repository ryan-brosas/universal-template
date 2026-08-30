<!-- capsule-v2 -->
# sqlSanitize DDL guards — how do `?` placeholders, dots-in-aliases, and attacker-controlled precision values survive being interpolated into SQL?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which string values are EVER safe to interpolate into generated SQL, and what three helpers enforce that boundary?

## Question-mark escaping + alias dot-repair + dtxp injection gate

**Path/Symbol:** `packages/nocodb/src/helpers/sqlSanitize.ts:sanitize` (:3–8), `unsanitize` (:10–13), `pgQuoteLiteral` (:25–30), `sanitiseDataTypePrecision` (:51–70), `sanitizeAndEscapeDots` (:72–90).
**Signature:** `sanitiseDataTypePrecision(dtxp: string | number | null | undefined): string` — returns the validated value or THROWS; `pgQuoteLiteral(value: string): string` throws on null/undefined; `sanitize(v)` escapes unescaped `?` runs as `\?\?…`.
**Data Shape:** `dtxp` (data-type extra param) is the column-precision field from the UIDT pipeline; accepted shapes: numeric with optional `,scale` (`255`, `10,2`), bare `MAX` (normalized upper-case), enum/set lists of single-quoted literals with `''` escaping (`'a','b'`).

### Decisive source
```ts
// :32-38 — WHY the gate exists (comment verbatim)
// Validate a column precision/length value (`dtxp`) before it is interpolated
// into DDL. Unlike the data type (`dt`, guarded by `KnexClient.sanitiseDataType`),
// `dtxp` is not run through an allowlist anywhere in the column pipeline, so a
// crafted value such as `1) CHECK(1=0` would otherwise inject a persistent
// constraint — or, on SQLite, an arbitrary `;`-delimited statement — into the
// live table schema.
```

**Flow:** `sanitize/unsanitize` are a paired escape codec for literal question marks inside identifiers/aliases that would otherwise be eaten by knex binding (`([^\\]|^)(\?+)` → backslash-escaped; unsanitize reverses `\?`). `sanitizeAndEscapeDots` renders an alias through `knex.raw('??', …)` then UNESCAPES the quote-wrapped dots (`` `.` `` → `.` on mysql, `"."` → `.` on pg) because PG/MySQL treat a quoted dotted identifier as one name while NocoDB needs multi-part resolution. `pgQuoteLiteral` exists for the narrow set of DDL positions where PG REJECTS bind parameters (CREATE TYPE … AS ENUM, ALTER TYPE ADD/RENAME VALUE, SET DEFAULT, USING expressions) — doubles single quotes only; identifiers must still go through `??`. `sanitiseDataTypePrecision` is the allowlist gate: `/^\d+(?:\s*,\s*\d+)?$/`, `/^max$/i`, or full-list enum regex `/^'(?:[^']|'')*'(?:\s*,\s*'(?:[^']|'')*')*$/`; anything else throws `Invalid data type precision: <value>` mirroring sanitiseDataType's throw style.
**Invariant:** (1) The comment's threat model is persistent schema injection: a bad dtxp doesn't just break one query, it writes a CHECK (or executes `;`-statements on SQLite) into the LIVE table. (2) pgQuoteLiteral is for VALUE literals in DDL ONLY — using it for identifiers reintroduces injection; the doc comment draws exactly this line. (3) The escape codec means every consumer of user-supplied alias strings must round-trip sanitize→unsanitize or leave stray backslashes behind.

### Porting traps (each verified against source)
- The MAX normalization accepts any casing (`max`, `Max`) but always returns `'MAX'` — MSSQL large-value types store `MAX` verbatim as dtxp (:62–64).
- In-file anchors: `grep -n 'persistent' src/helpers/sqlSanitize.ts` → :37 region; `grep -c "replace(/'/g" …` → 1; `grep -c "case 'mysql':" …` → 1.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'Invalid data type precision' src/helpers/sqlSanitize.ts | cut -d: -f1` → `69` and `sed -n '60,67p' src/helpers/sqlSanitize.ts | grep -ciE 'max|enum'` → `4` (lines :62/:63/:64 carry MAX-normalization comment+code, :66 the enum-list comment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "pgQuoteLiteral sanitiseDataTypePrecision sanitizeAndEscapeDots", limit: 10 });
```
Resolves all three symbols line-exact rank-1/2/3 in `sqlSanitize.ts` (:25-30/:51-70/:72-90).

## Verdict
Adopt the three-guard boundary (bind-or-quote-literal rule, dtxp allowlist-before-interpolation, alias dot-repair) verbatim; adapt regex dialects when porting beyond knex; omit nothing silently. Coverage caveat: no direct tests at pin; probes are source-greps.
