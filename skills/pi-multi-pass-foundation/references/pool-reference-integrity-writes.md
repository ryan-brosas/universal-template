<!-- capsule-v2 -->
# Pool reference integrity writes — how do rename and delete of a pool keep chains coherent without ever leaving a dangling reference?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** When a named pool is renamed or deleted, how do you update every chain entry that points at it — and report exactly what changed — in one atomic config write?

## Pure reference kernels + confirm-then-mutate-then-save-reload flows
**Path/Symbol:** `extensions/multi-sub.ts`: `renamePoolReferences` (3424-3438), `pruneRemovedPoolReferences` (3440-3460), `renamePoolConfig` (3462-3496), `removePoolConfig` (3986-4021), `reloadPoolManagerForCurrentProject` (3417-3422).
**Signature:** `function renamePoolReferences(chains: ChainConfig[], previousName: string, nextName: string): number`; `function pruneRemovedPoolReferences(chains: ChainConfig[], removedPoolNames: Set<string>): { chains; removedEntries; removedChains }`.
**Data Shape:** both kernels RETURN an audit count (renamed entries / removed entries + removed chains) so the UI message is derived from what actually changed, never from intent.

### Decisive source
```ts
// rename: in-place entry rewrite, count returned
for (const chain of chains) {
	for (const entry of chain.entries) {
		if (entry.pool !== previousName) continue;
		entry.pool = nextName;
		updatedEntries += 1;
	}
}
// prune: filter entries, then drop chains left with zero entries, counting both
chain.entries = chain.entries.filter((entry) => !removedPoolNames.has(entry.pool));
removedEntries += beforeCount - chain.entries.length;
const remainingChains = chains.filter((chain) => {
	if (chain.entries.length > 0) return true;
	removedChains += 1;
	return false;
});
// removePoolConfig flow around the kernel:
const confirmed = await ctx.ui.confirm("Confirm removal",
	referencedEntries > 0 ? `...will also remove ${referencedEntries} chain entr...` : `...`);
if (!confirmed) return false;
config.chains = pruned.chains;
config.pools = config.pools.filter((c) => c.name !== pool.name);
saveGlobalConfig(config);
reloadPoolManagerForCurrentProject(ctx, poolManager);   // poolManager.loadPools(loadEffectiveConfig(ctx.cwd).pools)
```

**Flow:** rename: cancel/blank/no-change/duplicate-name guards all return BEFORE mutation -> `pool.name = trimmedName` then `renamePoolReferences` rewrites every matching chain entry -> saveGlobalConfig -> reload PoolManager from the re-loaded effective config. Remove: PRE-count referencing chain entries across all chains for the confirmation text (subscriptions are explicitly kept) -> confirm gate -> prune chain references (dropping emptied chains) -> filter the pool out -> save -> reload -> notify with the exact removedEntries/removedChains counts.
**Invariant:** every mutating flow follows confirm -> mutate -> save -> reload, and the reload re-derives pools from loadEffectiveConfig so the live PoolManager can never disagree with the just-written file; reference repair uses the same kernels for direct edits and cascading teardowns; a rename collision is rejected before any write, so chains can never point at two pools or at none.
**Probe:** `node tests/pool-edit-check.mjs` (behavioral twins: runRenamePoolReferenceCheck pins 2 entries rewritten "work"->"office" with untouched "backup"; runRemovePoolReferenceCheck pins removedEntries=2, removedChains=1, surviving chain keeps only the backup entry; green at b9d9d1d7a092).
**Coverage note:** extensions/multi-sub.ts and tests/pool-edit-check.mjs indexed FULL, no_recorded_issue, generation match 2026-08-24T14:18:05Z; cited ranges read directly and byte-matched against graph snippets at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "renamePoolReferences pruneRemovedPoolReferences removePoolConfig reloadPoolManagerForCurrentProject", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt pure reference-repair kernels that return audit counts, pre-counted confirmation prompts that disclose collateral damage before it happens, empty-container deletion as part of pruning, and save-then-reload-from-disk as the single state transition. Adapt ui.confirm/ui.notify to your host's dialog surface. Omit pi ExtensionContext plumbing and the TUI menu handlers that wrap these flows.
