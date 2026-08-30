<!-- capsule-v2 -->
# Mnemonic query cache + cost log — tiered recall caching, zero-safe estimates

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/mnemopi/src/core/query-cache.ts`, `cost-log.ts`. **Question:** How do you cache expensive recall lookups across exact/semantic/fuzzy tiers without lying about hit equivalence, and log estimated LLM costs safely?

## Query cache: exact, semantic, and word-overlap tiers
**Path/Symbol:** `query-cache.ts:isQueryCacheEnabled` (46), `class QueryCache` (50+; `get` 130–195, `put` 199, `invalidate` 119, `stats` 226).
**Signature:** `get(query, embedding?): readonly QueryCacheResult[] | null`; `put(query, results, embedding?): void`; `isQueryCacheEnabled(useCache = true, env) = useCache && enhancedRecallEnabled(env)`.
**Data Shape:** `#tier1` and `#tier4` map normalized keys to results; `#tier23` maps a key to `{ embedding, results }`; `#insertTimes` provides TTL and LRU bookkeeping. Optional SQLite rows are `{ normalized, embedding_json, results_json }`; options accept camel- and snake-case database, size, and TTL keys.

### Decisive source
```ts
const cosine = cosineSimilarity(embedding, cached.embedding);
if (cosine >= 0.88) { bestScore = cosine; bestKey = cachedKey; break; }        // tier2
if (cosine >= 0.78) {                                                          // tier3
  const jaccard = this.jaccardWords(query, cachedKey);
  if (jaccard >= 0.15 && cosine > bestScore) { bestScore = cosine; bestKey = cachedKey; }
}
// tier4 word-overlap fallback:
if (overlap >= queryWords.size * 0.7 && overlap >= 2) return results;
```

**Flow:** `normalize` lowercases, removes one-character words, and sorts remaining terms. Lookup: expire-then-check tier1 exact-normalized first → tier2 high-cosine (≥0.88, early break) → tier3 cosine ≥0.78 AND Jaccard ≥0.15 → tier4 word-overlap fallback (≥70% of query words, minimum 2). Every hit refreshes LRU order (`#touchKey`) and records a persistent hit; misses increment counters per tier. `put` owns population + optional persistence; `invalidate` clears every tier, deletes persisted rows, and bumps `version`. TTL keeps original insert time; map order supplies LRU eviction at `maxSize`.

**Invariant:** tier1 is exact after normalization; tiers 2–4 intentionally return candidates from a RELATED cached key — consumers must not treat them as exact-answer equivalence. Callers honoring `isQueryCacheEnabled` bypass the cache entirely when the feature flag is off.

**Probe:** `test/query-cache-synonyms.test.ts` checks all four tiers, TTL, invalidation, LRU eviction, persistence, stats, and the `MNEMOPI_ENHANCED_RECALL` gate. Coverage caveat: tests excluded from graph index by design.

## Cost log: durable estimate rows with zero-safe aggregates
**Path/Symbol:** `cost-log.ts:getConn` (22), `initCostLog` (27), `logCost` (45), `getCostStats` (66).
**Signature:** `logCost(sessionId, memoryCount, tokenCount, estimatedCostUsd, model = "default", dbPath?): void`; `getCostStats(sessionId?, dbPath?): CostStats`.
**Data Shape:** `cost_entries { id, session_id, memory_count, token_count, estimated_cost_usd, model, timestamp }`; `CostStats { total_calls, total_memories_injected, total_tokens, total_estimated_cost_usd }`.

### Decisive source
```sql
INSERT INTO cost_entries (session_id, memory_count, token_count,
  estimated_cost_usd, model, timestamp) VALUES (?, ?, ?, ?, ?, ?)
-- aggregation coalesces COUNT/SUM nulls to 0 and rounds USD to six decimals
```

**Flow:** each log call initializes the local SQLite table, inserts one model-cost estimate row, and closes its connection. `getCostStats` aggregates every session or one session; missing rows resolve to zero totals rather than an error.

**Invariant:** `estimated_cost_usd` is a MODEL estimate, never a billing record; per-session filtering cannot leak rows across sessions; an absent session stays zero-valued.

**Probe:** `test/text-utilities.test.ts` initializes the table, writes multiple sessions, and asserts all-session, one-session, and missing-session totals.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(QueryCache|isQueryCacheEnabled|initCostLog|logCost|getCostStats)$", limit: 8, fields: ["signature"] });
```

## Verdict
Adopt the four-tier lookup ladder with explicit similarity thresholds, LRU+TTL bookkeeping, feature-gated caching, and zero-coalescing cost aggregation; adapt thresholds, normalization rules, and storage to host; omit SQLite persistence if recall is single-process in-memory.
