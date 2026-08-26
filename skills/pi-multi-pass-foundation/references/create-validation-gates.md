<!-- capsule-v2 -->
# Create-time validation gates — what must be true about a pool or chain BEFORE it is allowed into persisted config?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How do you validate a new pool/chain definition against the CURRENT config so an invalid combination (empty pool, duplicate name, chain entry pointing at a missing pool or unavailable model) can never reach disk?

## Single validator returning one first-error string, checked before persist
**Path/Symbol:** `extensions/multi-sub.ts`: `createChainValidationError` (3795-3824), `getSelectableModelsForPool` (3791-3793), `findChainByName` (4287-4289); pool-side twin `createPoolValidationMessage` (tests/pool-edit-check.mjs:3-8, mirroring the source's "Pool needs at least 1 member." gate).
**Signature:** `function createChainValidationError(config: MultiPassConfig, chain: ChainConfig): string | null`; `function getSelectableModelsForPool(pool: PoolConfig): string[]`.
**Data Shape:** validators return `null` = valid, otherwise ONE human-readable error for the FIRST violated rule — callers notify and abort without partial writes.

### Decisive source
```ts
function createChainValidationError(config: MultiPassConfig, chain: ChainConfig): string | null {
	if (!chain.name.trim()) return "Chain name is required.";
	if (findChainByName(config.chains, chain.name)) return `Chain "${chain.name}" already exists.`;
	if (chain.entries.length === 0) return `Chain "${chain.name}" needs at least 1 entry.`;
	for (const entry of chain.entries) {
		const pool = config.pools.find((candidate) => candidate.name === entry.pool);
		if (!pool) return `Chain entry pool "${entry.pool}" does not exist.`;
		const selectableModels = getSelectableModelsForPool(pool);
		if (selectableModels.length === 0)
			return `Pool "${pool.name}" has no selectable models for ${pool.baseProvider}.`;
		if (!selectableModels.includes(entry.model))
			return `Model "${entry.model}" is not available for pool "${pool.name}".`;
	}
	return null;
}
// model availability is defined by the BASE provider catalog, not the clone:
return (getModels(pool.baseProvider as any) as Model<Api>[]).map((model) => model.id);
```

**Flow:** structural rules first (non-blank unique name, at least one entry) -> then referential rules per entry in order: target pool exists in current config -> that pool's base provider still yields selectable models -> the requested model id is IN that set -> only when every rule passes does the caller persist via buildChainConfig/buildPoolConfig + saveGlobalConfig; any failure notifies the single error and writes nothing.
**Invariant:** validation runs against the LIVE merged config, so uniqueness and existence checks see everything already on disk plus this session's edits; a chain entry's model must exist in the base provider's catalog even though routing later resolves it under the clone name — availability is judged once, at the source of truth; validators never mutate; the null-or-first-error contract keeps failure handling trivial for callers.
**Probe:** `node tests/pool-edit-check.mjs` runPoolValidationChecks pins the pool-side gate (`createPoolValidationMessage([])` = "Pool needs at least 1 member.", non-empty = null; green at b9d9d1d7a092). COVERAGE CAVEAT: no check script drives `createChainValidationError` directly; its ladder was verified by direct source read at the pin only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "createChainValidationError getSelectableModelsForPool findChainByName buildChainConfig", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt validate-against-live-config with a null-or-first-error contract, ordered structural-before-referential rules, and base-catalog-defined model availability. Adapt getModels to your host's model registry and the error strings to your UX voice. Omit the TUI promptForPoolDefinition wizard that feeds these validators.
