<!-- capsule-v2 -->
# Web-queries sentinel — how do you record "a search happened but the queries are secret"?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should providers report fan-out searches they cannot observe, without fabricating data or silently dropping the signal?

## One shared constant, written by producers, filtered by every reader
**Path/Symbol:** `packages/lib/src/constants.ts:WEB_QUERIES_UNAVAILABLE` (L55), consumed in `dataforseo.ts` L139/L174/L281/L313; filtered at read time by `apps/web/src/lib/fanout-analysis.ts:UNAVAILABLE_SENTINEL` (L312).
**Signature:** `const WEB_QUERIES_UNAVAILABLE = "unavailable"`.
**Data Shape:** `prompt_runs.web_queries: string[]` — either real query strings, or exactly one `"unavailable"` marker, or empty.

### Decisive source
```ts
// Google AI Mode always searches, but DataForSEO doesn't expose the query
// strings anywhere in its response. Mark "unavailable" when citations
// prove a search, like the other providers; never echo the prompt as a query.
webQueries: citations.length > 0 ? [WEB_QUERIES_UNAVAILABLE] : [],
```
And the read side:
```ts
export const UNAVAILABLE_SENTINEL = WEB_QUERIES_UNAVAILABLE; // aliases the constant the
// provider implementations write, so the two sides can't drift.
```

**Flow:** producer ladder per run: real fan-out list if exposed → else `[unavailable]` when citations prove a search ran → else `[]`. The worker stores `webQueries` verbatim ("engines do sometimes genuinely search the prompt verbatim, and that's real data"); verbatim repeats are excluded only at display time as a read-time rule.
**Invariant:** NEVER echo the tracked prompt itself as a fan-out query — that fabricates an expansion that never happened. The sentinel must be produced and consumed through the single constant or the filter silently rots.
**Probe:** `packages/lib/src/providers/registry/dataforseo.test.ts` scraper route pins `result.webQueries` to the real `fan_out_queries`; text-extraction + fanout suites keep both sides honest.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "WEB_QUERIES_UNAVAILABLE webQueries fan_out_queries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state encoding (real / unavailable-marker / none) for any unobservable-by-design telemetry field; adapt the marker string if you persist it (keep it a shared constant); omit nothing — this is small but every wrong port (echoing the prompt, dropping the marker) corrupts analytics quietly.
