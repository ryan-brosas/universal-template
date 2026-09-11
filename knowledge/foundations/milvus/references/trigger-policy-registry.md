<!-- capsule-v2 -->
# Compaction trigger manager ticker lattice — how do six independent policies share one inspector capacity without thundering-herd re-planning?

**Source:** Milvus Apache-2.0 `master@034e9fbba47aac1346caed8bf9df8d612297e5d7`; Codebase Memory `ext-milvus`. **Question:** (companion to trigger-manager-ticker-lattice) What does the full policy registry look like at construction, and which policies are conditionally registered?

## Policy registry construction
**Path/Symbol:** `internal/datacoord/compaction_trigger_v2.go:NewCompactionTriggerManager` (lines 159–192).
**Signature:** `func NewCompactionTriggerManager(alloc allocator.Allocator, handler Handler, inspector CompactionInspector, meta *meta, versionManager IndexEngineVersionManager) *CompactionTriggerManager`.
**Data Shape:** Six concrete policies: l0, clustering, single, forceMerge, storageVersionUpgrade, bumpSchemaVersion + optional targetReconciler. Registry: `policies map[TickerType]CompactionPolicy` where TargetTicker entry exists ONLY when `EnableTargetBasedCompaction`.

### Decisive source
```go
m.l0Policy = newL0CompactionPolicy(meta, alloc)
m.clusteringPolicy = newClusteringCompactionPolicy(meta, m.allocator, m.handler)
m.singlePolicy = newSingleCompactionPolicy(meta, m.allocator, m.handler)
m.forceMergePolicy = newForceMergeCompactionPolicy(meta, m.allocator, m.handler)
m.upgradeStorageVersionPolicy = newStorageVersionUpgradePolicy(meta, m.allocator, m.handler, versionManager)
m.bumpSchemaVersionPolicy = newBumpSchemaVersionPolicy(meta, m.allocator, m.handler)
if Params.DataCoordCfg.EnableTargetBasedCompaction.GetAsBool() {
    m.targetReconciler = newCompactionTargetReconciler(meta, handler)
}
// Initialize policies map for ticker handling
m.policies[L0Ticker] = m.l0Policy
...
if m.targetReconciler != nil {
    m.policies[TargetTicker] = m.targetReconciler
}
```

**Flow:** Construction wires every policy with its dependencies (allocator shared; handler for collection lookups; versionManager only for storage-version). The reconciler is the one CONDITIONAL registration — absent the config flag, its ticker case checks `policies[TargetTicker]` existence before firing (:258–260). Force-merge has no ticker (manual-only) but still gets constructed for InitForceMergeMemoryQuerier late-binding of its topology querier.
**Invariant:** Registration in the map IS enablement for ticked policies; per-fire Enable() checks are a second layer (e.g., EnableAutoCompaction flips L0/single off without rebuilding). Manual-only policies must be excluded from the ticker map or they'd need null Trigger bodies. Late dependency injection (SetTopologyQuerier after construction) requires nil-tolerance in the policy.
**Probe:** Direct-source pin: conditional registration :178–190. Upstream suite `TestCompactionTriggerManagerSuite` covers registry behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-milvus", query: "NewCompactionTriggerManager policies TickerType targetReconciler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit policy-registry construction with optional registration for feature-flagged schedulers. Adapt dependency injection style to your container. Omit milvus param table specifics. Caveat: cgo-blocked runner; direct source read at pin.
