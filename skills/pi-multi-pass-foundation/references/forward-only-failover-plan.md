<!-- capsule-v2 -->
# Forward-only failover plan — how are failover candidates ordered with an auditable skip taxonomy?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** When an account hits a rate limit, how do you produce the ordered list of next targets — and make every exclusion explainable — without ever moving backwards?

## Ring walk inside the pool, then strictly forward along the chain
**Path/Symbol:** `extensions/multi-sub.ts`: `PoolManager.buildFailoverPlan` (2251-2393), `findApplicableChain` (2238-2249), `classifyPoolMemberSkip` (4403-4426), `classifyChainEntrySkip` (4428-4459); types `FailoverPlan`/`FailoverSkip` (4341-4353 region).
**Signature:** `buildFailoverPlan(currentModel: Model<Api>, config: MultiPassConfig, authStorage: { hasAuth(p: string): boolean }, options?: { attemptedProviders?: Set<string>; visitedChainIndexes?: Set<number> }): FailoverPlan`.
**Data Shape:** FailoverPlan = {pool?, chain?, currentChainIndex?, candidates: FailoverCandidate[], skips: FailoverSkip[]}; candidate = {poolName, provider, modelId, source: "pool"|"chain", chainName?, chainIndex?}; skip = {type: "pool-member"|"chain-entry", poolName, reason, detail, chainName?, chainIndex?}.

### Decisive source
```ts
const startIndex = currentIndex >= 0 ? currentIndex : 0;
for (let step = 1; step <= poolSize; step++) {
	const candidateIndex = poolSize <= 0 ? -1 : (startIndex + step) % poolSize;
	if (candidateIndex < 0) break;
	const candidate = pool.members[candidateIndex];
	if (candidate === currentModel.provider) continue;
	if (attemptedProviders.has(candidate)) { skips.push({ type: "pool-member", ..., reason: "already-attempted", ... }); continue; }
	const skip = classifyPoolMemberSkip(pool.name, candidate, authStorage, this.isMemberExhausted(pool, candidate));
	if (skip) { skips.push(skip); continue; }
	candidates.push({ poolName: pool.name, provider: candidate, modelId: currentModel.id, source: "pool" });
}
const applicable = this.findApplicableChain(pool.name);
if (!applicable) return { pool, candidates, skips };
for (let chainIndex = applicable.index + 1; chainIndex < applicable.chain.entries.length; chainIndex++) {
	// visited-chain-index / disabled-entry / missing-pool / member-level skips -> typed skip entries
	// eligible members pushed with source: "chain"
}
```

**Flow:** locate the pool owning the current provider (none -> empty plan) -> ring-walk members from currentIndex+1 modulo size, skipping self, already-attempted-this-turn, no-auth, exhausted/cooldown — each exclusion becomes a typed skip with a human-readable detail -> if the pool belongs to an enabled chain, continue STRICTLY FORWARD from currentChainIndex+1 to the end -> per chain entry: classify entry-level skips (disabled-entry, missing-pool via getChainEntryIssue -> disabled-pool/unavailable-model), filter target-pool members through the SAME attempted+auth+exhausted gate (annotating skips with chainName/chainIndex), record no-eligible-members when a whole target pool is dry.
**Invariant:** never backwards — pool candidates start after the current index and chain traversal starts after the current chain position; attempted/visited sets passed in by the caller are honored, not reset; planning is READ-ONLY (no state mutation, no config writes); every non-selection is visible as a structured skip, so "why did it pick X" is always answerable.
**Probe:** `node tests/runtime-failover-check.mjs` (default runCoreChecks pins plan ordering + skip reasons against the RuntimeHarness twin at tests/runtime-failover-check.mjs:188-306; green at b9d9d1d7a092).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "buildFailoverPlan classifyPoolMemberSkip classifyChainEntrySkip", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt plan-then-execute separation: one pure planner returning candidates + typed skips, consumed by a separate executor. Adapt Model/authStorage resolution to your registry. Omit pi's ExtensionContext plumbing and UI notification strings (formatFailover* helpers) or re-word them for your host.
