<!-- capsule-v2 -->
# Import error formatter — how do raw DB errors become row-precise, column-attributed messages a user can act on?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does describeRowError map driver exceptions to human guidance, optionally using the offending row?

## describeRowError with embedded-value matching
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/error-formatter.ts:describeRowError` (whole, 100L); call sites `data-import.processor.ts:824, 850`.
**Signature:** `describeRowError(err: any, row?: Record<string, any>): string`.
**Data Shape:** input = thrown error (driver text may embed the failing value, e.g. `numeric: "$500.00"`); optional row lets the formatter attribute the value to its column title.

### Decisive source
```ts
// batch-level: no row context available
stats.errors.push({ row: batchStartRow, error: describeRowError(err) });
// single-row retry: pass the row so an embedded value can be matched back
stats.errors.push({ row: batchStartRow + i,
                    error: describeRowError(rowErr, pending[i]) });
```

**Flow:** driver messages arrive as opaque strings; the formatter recognizes common patterns (numeric/decimal rejections, unique-constraint text, JSON parse failures) and, when the caller supplies the retried row, scans cell values to name the exact source column that produced the failure. Output is a single user-safe sentence stored in `stats.errors`.
**Invariant:** never leak raw driver/schema detail when no pattern matches — fall back to generic wording (mirrors the run()-level NcBaseErrorv2 sanitization). The two-arity design is deliberate: batch failures have no single row; only the one-by-one retry path can attribute columns.
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:845-851` — comment "so the formatter can match an embedded value (e.g. numeric: \"$500.00\") back to its column name" directly above the row-passing call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "describeRowError error-formatter import", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-tier error attribution (batch vs row) with pattern-based sanitization; adapt recognized patterns to your driver's message formats; omit value-matching if your DB returns structured error codes (then switch on codes instead). Coverage caveat: no in-repo tests; source-grounded.
