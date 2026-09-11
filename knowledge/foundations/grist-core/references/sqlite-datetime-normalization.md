<!-- capsule-v2 -->
# SQLite datetime normalization seam — why do string timestamps from SQLite need forcing through moment.utc?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are heterogeneous timestamp inputs (Date | string | number) turned into one ISO8601-with-zone form?

## Date objects → toISOString directly; strings/numbers FORCED via moment.utc because SQLite strings carry no zone
**Path/Symbol:** `app/common/normalizedDateTimeString.ts`: whole file (:15–27); consumed by ActiveDoc snapshot-progress reporting (`app/server/lib/ActiveDoc.ts` :3137–3138).
**Signature:** `normalizedDateTimeString(dateTime: any): string`.
**Data Shape:** Returns ISO8601 string; throws on anything else (loud, not silent).

### Decisive source
```ts
// Timestamps in SQLite are stored as UTC, and read as strings
// (without timezone information). The normalization here is pretty important.
if (dateTime instanceof Date) {
  return moment(dateTime).toISOString();
}
if (typeof dateTime === "string" || typeof dateTime === "number") {
  // When SQLite returns a string, it will be in UTC.
  // Need to make sure it actually have timezone info in it (will not by default).
  return moment.utc(dateTime).toISOString();
}
throw new Error(`normalizedDateTimeString cannot handle ${dateTime}`);
```

**Flow:** falsy passes through unchanged (`!dateTime` early return preserves "" / null semantics for callers distinguishing "no time yet") → Date instances already carry zone info → string/number path re-anchors to UTC BEFORE formatting so the emitted string always ends in Z.
**Invariant:** `moment.utc(x)` vs `moment(x)` differs precisely when x lacks zone markers: local-time interpretation would shift every SQLite-read timestamp by the host offset. Postgres drivers return real Date objects where the comment says normalization "is not really needed" — the branch split encodes driver behavior knowledge. Unknown types throw rather than guess (audit-visible).
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "moment.utc(dateTime).toISOString()" app/common/normalizedDateTimeString.ts && grep -n "lastChangeAt: normalizedDateTimeString" app/server/lib/ActiveDoc.ts'` → :24 and :3137 consumer proof.
Direct tests: no dedicated spec file (27L util); covered indirectly via doc-snapshot suites — stated coverage caveat.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"normalizedDateTimeString moment utc iso","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the branch split (driver-aware) and throw-on-unknown; adapt output format to your log schema; omit only if your storage layer returns zoned Dates exclusively.
