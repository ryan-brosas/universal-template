<!-- capsule-v2 -->
# Deferred LTAR link phase — how are link columns imported after rows exist, with bounded memory even for files bigger than RAM?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the importer resolve display values to record ids and create links without holding every intent in memory?

## linkAccumulator + flush threshold + self-ref deferral
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:streamSheetData` bookkeeping (699-738), `flushLinks` (858-876), `processLinks` (935-1081).
**Signature:** `linkAccum: Map<colId, Array<{pk, values[]}>>`; `getLinkFlushThreshold(): number` (env `NC_DATA_IMPORT_LINK_FLUSH_THRESHOLD`, default 50 000); `processLinks({linkAccum, resolvedCache?})`.
**Data Shape:** per-column display-value→pk cache `Map<colId, Map<value, pk|null>>` (`null` = resolved-but-unmatched); resolve chunks of 200 values/query; link writes at concurrency 25.

### Decisive source
```ts
// Self-referential links may point at rows LATER in the same file → must wait
let hasSelfRefLink = false;
if (colOpt?.fk_related_model_id === model.id) { hasSelfRefLink = true; break; }
...
if (!hasSelfRefLink && pendingLinkRows >= linkFlushThreshold) { await flushLinks(); }
...
// cross-flush cache: each distinct value resolved at most once per import
const cached = colCache?.get(v);
if (cached === undefined) toResolve.push(v);
else if (cached !== null) valueToPk.set(v, cached);
// unmatched recorded too — never re-queried:
} else { colCache?.set(v, null); }
```

**Flow:** during row streaming only `{pk, displayValues[]}` intents accumulate; at threshold (or end) `processLinks` dedupes values, batch-resolves them case-insensitively against related tables, then `addLinks` per parent row (append-only; import never unlinks). Unmatched values count as `valuesUnmatched`; matched-but-failed writes count separately as `linksFailed`.
**Invariant:** a self-referential column disables ALL mid-stream flushing for that sheet — forward references ("row 5 links to row 9000") resolve wrongly otherwise; memory in that rare case is bounded by the file-size cap. The cache must store negative results too, or repeated unmatched values re-query every flush.
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:723-738` — hasSelfRefLink detection loop over mapped LTAR cols comparing `fk_related_model_id === model.id`; `:1012-1024` — chunked resolve writing both hits and misses into colCache.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "processLinks linkAccum flushLinks resolvedCache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt deferred two-phase insert-then-link with threshold flushing, self-reference detection, and negative-caching resolution; adapt delimiter defaults, chunk sizes, and addLinks transport to host; omit UI progress JSON shape. Coverage caveat: no in-repo tests; source-grounded.
