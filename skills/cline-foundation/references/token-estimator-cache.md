<!-- capsule-v2 -->
# Token estimator cache — WeakMap-memoized per-message estimates with serialization fallback

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How are per-message token counts estimated cheaply and consistently across trigger checks, selection walks, and projections?

## Identity-keyed memo; JSON length ÷ CHARS_PER_TOKEN, prose-serialization fallback
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction-shared.ts:184-202` (`createTokenEstimator`) + `:72-77` (`truncateText`), re-export of `CHARS_PER_TOKEN`/`estimateTokens` from `@cline/shared`.
**Signature:** `createTokenEstimator() → (message) => number`; closure holds `WeakMap<object, number>` keyed by message object identity.
**Data Shape:** Primary metric = `estimateTokens(JSON.stringify(message).length)`; on stringify failure (circular etc.) falls back to `serializeMessage` prose (`[User]: …`, `[Bot tool calls]: name(json)`, `[Tool result]: …`, images as `[image:type]`, thinking truncated at 2000 chars).

### Decisive source
```ts
const cache = new WeakMap<object, number>();
return (message) => {
    const cached = cache.get(ref);
    if (typeof cached === "number") { return cached; }
    let serialized: string;
    try { serialized = JSON.stringify(message); }
    catch { serialized = serializeMessage(message); }
    const value = estimateTokens(serialized.length);
    cache.set(ref, value);
    return value;
};
```

**Flow:** every plane (trigger gate, findCutIndex walk, basic-compaction budgeting, budget projection totals) receives ONE estimator instance per prepareTurn so all comparisons share a unit; WeakMap means mutated messages get fresh estimates without manual invalidation and dropped messages GC naturally.
**Invariant:** Estimates are CHAR-based (÷ CHARS_PER_TOKEN), deliberately conservative vs real tokenizers — the whole stack tolerates drift via the trigger ratio margin, the overflow-recovery escape hatch, and basic compaction's floor valve; never mix two estimator instances in one comparison. Upstream test pins "falls back to serialized character estimation when metrics are incomplete" and "does not treat cumulative request metrics as per-message token counts".
**Probe:** `grep -cF 'const cache = new WeakMap<object, number>();' .../compaction-shared.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "createTokenEstimator estimateTokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity-memoized estimation with one instance per pipeline; adapt CHARS_PER_TOKEN to host tokenizer; omit the prose serializer if messages are always JSON-safe. Runner blocked honestly; battery greps green.
