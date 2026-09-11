<!-- capsule-v2 -->
# Restart-worthiness matrix — which config changes rebuild the service graph versus hot-apply?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** Given a previous config snapshot and a new one, does the code-index service need full recreation?

## Critical-change ladder with a dimension-only exception
**Path/Symbol:** `src/services/code-index/config-manager.ts:doesConfigChangeRequireRestart/_hasVectorDimensionChanged` (:295-440).
**Signature:** `doesConfigChangeRequireRestart(prev: PreviousConfigSnapshot): boolean`; snapshot captured BEFORE `refreshSecrets()` re-reads storage.
**Data Shape:** snapshot carries enabled/configured/provider/modelId/modelDimension/every credential/qdrant url+key; search-min-score is deliberately ABSENT (minor change).

### Decisive source
```ts
if (prevModelDimension !== currentModelDimension) { return true }
...
if (this._hasVectorDimensionChanged(prevProvider, prev?.modelId)) { return true }
// inside _hasVectorDimensionChanged:
if (prevDimension === undefined || currentDimension === undefined) { return true } // unknown ⇒ safe restart
return prevDimension !== currentDimension // SAME dimension model swap = NO restart
```

**Flow:** ladder order: disabled→enabled transition ⇒ restart; enabled→disabled ⇒ restart; both-unready ⇒ no restart; then any provider/credential/baseURL/qdrant-key/dimension change ⇒ restart; FINALLY model-id swaps are resolved through the registry — swapping models WITHIN the same vector dimension (e.g. two 1536-dim models) does NOT restart, because the collection geometry is unchanged.
**Invariant:** restart decisions protect Qdrant collection compatibility, not correctness of future requests — that's why minScore changes skip it. The unknown-dimension fail-safe (restart when lookup fails) prevents creating points against an assumed dimension.
**Probe:** `src/services/code-index/__tests__/config-manager.spec.ts`; executed pins: dimension-equality branch + fallback-to-openai default forms.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "doesConfigChangeRequireRestart _hasVectorDimensionChanged PreviousConfigSnapshot", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt snapshot-then-compare with explicit critical-field lists and dimension-aware model swaps. Adapt field set to your providers. Omit ContextProxy plumbing.
