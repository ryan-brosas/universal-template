<!-- capsule-v2 -->
# Model resolution merge — how do four catalog sources combine without stale limits, lost headers, or lying authority?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** What is the precedence and merge policy when static bundled rows, a fallback feed, the cache, and live discovery disagree?

## static → modelsDev → cache → dynamic with per-field preference ladders
**Path/Symbol:** `packages/catalog/src/model-manager.ts:resolveProviderModels` (:178), `restoreCachedModelHeaders` (:129), `shouldFetchRemoteSources` (:368), `prepareCacheModelsForStaticMismatch` (:395), `mergeDynamicModel` (:488), `preferDiscoveryLimit` (:557), `fingerprintStatic` (:471).
**Signature:** `resolveProviderModels(options, strategy: "online"|"offline"|"online-if-uncached"): Promise<{models, stale}>`.
**Data Shape:** `NON_AUTHORITATIVE_RETRY_MS = 5min` vs `DEFAULT_CACHE_TTL_MS = 2h` — failed dynamic fetches retry on the short clock; static fingerprint = `merge-v3:<Bun.hash(JSON.stringify(statics)).toString(36)>` (+ `:drop:` hash of migration ids), cached by reference via a Symbol tag.

### Decisive source
```ts
// A successful EMPTY result stays authoritative for THIS cycle (an
// intentional catalog emptying still prunes removed models downstream),
// but is NOT pinned into the cache as authoritative — that would suppress
// the short retry that recovers a transient empty response (#6620). Result
// authority vs cache retry are deliberately separate concerns.
const dynamicCacheAuthoritative = dynamicFetchSucceeded && dynamicModels.length > 0;

// Discovery resolving the same id to a DIFFERENT endpoint invalidates
// endpoint-pinned capabilities — its explicit image:false must not be
// OR-upgraded by the bundled reference.
const endpointChanged = existingModel.baseUrl !== dynamicModel.baseUrl;

// The one sentinel limit treated as unknown: discovery reporting 4096 while
// static knows better means discovery simply doesn't know.
if (discoveryLimit === 4096 && fallbackLimit !== null && fallbackLimit > discoveryLimit) return fallbackLimit;
```

**Flow:** read cache → restore omitted headers from static (same-id or `requestModelId`, gated by unrestorable markers + `header_restore_version` legacy carve-out) → fingerprint decides cold-start fast path (fresh authoritative cache + matching fingerprint ⇒ cache row IS the merged result, skipping ~800ms of rebuild) → fetch modelsDev + dynamic in parallel → merge by id with per-field ladders (name: non-id discovery name wins; cost: positive finite wins; limits: positive finite except 4096 sentinel; reasoning: OR unless provider-authoritative like Synthetic; input: OR unless endpoint changed) → authoritative mode prunes to discovered ids → collapse variants at the merge point → write snapshot (authoritative only when non-empty) → `stale` reports whether resolution is provider-complete.
**Invariant:** (1) empty-but-successful discovery prunes but never pins; (2) static-fingerprint mismatch SANITIZES same-id cache rows by nulling contextWindow/maxTokens so stale limits can't survive a catalog change (`dropCachedModelIdsOnStaticMismatch` forces full refetch for listed ids); (3) header-less restoration paths prefer dropping/refetching over returning a model with wrong auth; (4) rebuild always re-enters through `buildModel` from sparse `compatConfig`, never from resolved compat.
**Probe:** direct `packages/catalog/test/build.test.ts:1049` (static-mismatch limits refresh), `:1108` (empty-discovery retry + recovery caching), `:1162` (authoritative emptying prunes), `:820` (legacy OpenRouter rows ignored offline).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveProviderModels mergeDynamicModels staticFingerprint authoritative", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the source-precedence chain, per-field merge ladders, dual-retry clocks, and the authority/retry split; adapt the fingerprint scheme to your static catalog; omit modelsDev fallback if you have no third-party feed. Coverage caveat: none — resolveProviderModels has an extensive async test suite with fake fetchers.
