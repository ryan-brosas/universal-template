<!-- capsule-v2 -->
# Subscription teardown cascade — what is the safe order to delete one account when pools, chains, auth, and the provider registry all reference it?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** In which order must credentials, host registration, pool membership, chain references, and the config entry itself be torn down so no survivor dangles?

## Auth -> registry -> membership -> emptied pools -> chain prune -> entry -> save -> refresh x2
**Path/Symbol:** `extensions/multi-sub.ts`: `removeSubscriptionEntry` (2921-2959); kernels reused from the pool-reference-integrity capsule: `pruneRemovedPoolReferences` (3440-3460), `reloadPoolManagerForCurrentProject` (3417-3422).
**Signature:** `async function removeSubscriptionEntry(pi: ExtensionAPI, ctx: ExtensionCommandContext, config: MultiPassConfig, entry: SubEntry, poolManager: PoolManager): Promise<void>`.
**Data Shape:** identity key = `subProviderName(entry)`; removal matches the exact (provider, index) pair — never name-prefix matching.

### Decisive source
```ts
if (!confirmed) return;                                   // confirm gate before ANY mutation
const name = subProviderName(entry);
if (ctx.modelRegistry.authStorage.hasAuth(name)) {
	ctx.modelRegistry.authStorage.logout(name);            // 1. credentials first
}
pi.unregisterProvider(name);                              // 2. host registration

for (const pool of config.pools) {                        // 3. strip pool membership everywhere
	pool.members = pool.members.filter((member) => member !== name);
}
const removedPoolNames = new Set(                         // 4. pools left with zero members die...
	config.pools.filter((pool) => pool.members.length === 0).map((pool) => pool.name));
config.pools = config.pools.filter((pool) => pool.members.length > 0);
if (removedPoolNames.size > 0) {
	const pruned = pruneRemovedPoolReferences(config.chains, removedPoolNames); // 5. ...and their chain refs
	config.chains = pruned.chains;
}
config.subscriptions = config.subscriptions.filter(       // 6. exact (provider,index) entry removal
	(c) => !(c.provider === entry.provider && c.index === entry.index));

saveGlobalConfig(config);                                 // 7. ONE write for the whole cascade
ctx.modelRegistry.refresh();                              // 8. host model cache
reloadPoolManagerForCurrentProject(ctx, poolManager);     // 9. live rotation state from disk
```

**Flow:** confirmation discloses that auth will be logged out -> teardown proceeds strictly inward from runtime surfaces (credentials, then provider registration) toward durable config (membership, emptied pools, chain references, subscription entry) -> a single saveGlobalConfig commits the whole cascade atomically -> two refreshes re-synchronize the two independent caches (modelRegistry and PoolManager) with the written file.
**Invariant:** nothing is mutated before the confirm gate resolves; the deletion predicate is the exact (provider, index) pair, so a same-provider sibling account is untouched; emptied pools and their chain entries are pruned in the SAME pass (reuse of `pruneRemovedPoolReferences`), preserving the leaf-wide invariant that no chain references a nonexistent pool; exactly one config write covers all structural changes — partial saves are impossible.
**Probe:** `node tests/pool-edit-check.mjs` runRemovePoolReferenceChecks pins the mid-cascade kernel behavior (entries filtered, emptied chains counted and dropped). COVERAGE CAVEAT: no check script drives `removeSubscriptionEntry` end-to-end (it needs pi ExtensionAPI + UI); the ordering was verified by direct source read at the pin only — treat the sequence as source-verified, runner-untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "removeSubscriptionEntry unregisterProvider pruneRemovedPoolReferences reloadPoolManagerForCurrentProject", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt the ordered teardown: confirm -> logout -> unregister -> strip memberships -> drop emptied containers -> repair referencers -> remove the entry -> single save -> refresh every derived cache. Adapt authStorage/logout, pi.unregisterProvider, and the modelRegistry/PoolManager refresh pair to your host's equivalents. Omit the TUI confirm/notify transport.
