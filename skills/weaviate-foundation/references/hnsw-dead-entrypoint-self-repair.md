<!-- capsule-v2 -->
# Dead-entrypoint self-repair — entrypointDistWithRepair / repairGlobalEntrypoint termination ladder

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** What happens when a search starts from an entrypoint that was deleted (nil node / missing vector) under it?

## Repair loop + compare-and-swap replacement
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:826-855` (`entrypointDistWithRepair`), `delete.go:720-746` (`repairGlobalEntrypoint`), `:749-810` (`findNewGlobalEntrypoint`).
**Signature:** `entrypointDistWithRepair(ctx, distancer, entryPointID uint64, searchVec []float32) (uint64, float32, error)`; `repairGlobalEntrypoint(oldEntrypoint uint64, denyList AllowList) (uint64, error)`; sentinel `errNoUsableEntrypoint = errors.New("no valid entrypoint available")`.
**Data Shape:** denyList must ALREADY contain oldEntrypoint when passed in; callers translate `errNoUsableEntrypoint` into an EMPTY result (nil,nil,nil), not an error.

### Decisive source
```go
for {
    if h.nodeByID(entryPointID) != nil {
        dist, err := h.distToNode(distancer, entryPointID, searchVec)
        if err == nil { return entryPointID, dist, nil }
        var e storobj.ErrNotFound
        if !errors.As(err, &e) { return 0, 0, errors.Wrap(...) }
        h.handleDeletedDocOfNode(entryPointID, "entrypointDistWithRepair")  // tombstone + siblings
    }
    if err := ctx.Err(); err != nil { return 0, 0, err }
    newEp, err := h.repairGlobalEntrypoint(entryPointID, helpers.NewAllowList(entryPointID))
    if err != nil { return 0, 0, err }
    entryPointID = newEp   // each iteration either succeeds or rules out another dead node
}
// repairGlobalEntrypoint:
newEntrypoint, level, ok := h.findNewGlobalEntrypoint(denyList, oldEntrypoint)
if !ok {
    if currentEp := h.getEntrypoint(); currentEp != oldEntrypoint { return currentEp, nil } // lost race ⇒ reuse winner
    return 0, errNoUsableEntrypoint
}
h.Lock()
if h.entryPointID != oldEntrypoint { return h.entryPointID, nil }   // double-check under write lock
h.entryPointID = newEntrypoint; h.currentMaximumLayer = level
h.commitLog.SetEntryPointWithMaxLayer(newEntrypoint, level)
```

**Flow:** probe the entrypoint (nil? vector fetchable?) → on store-level deletion, tombstone the dead node AND its multivector doc-siblings (`handleDeletedDocOfNode`) → ask `repairGlobalEntrypoint` for a replacement → loop with the new id. Replacement scans ALL nodes for the highest-level live non-denied candidate (`findNewGlobalEntrypoint`), tolerating nodes whose level exceeds currentMaximumLayer (corrupt commit-log replay), and is guarded by two concurrency outs: bail if another writer already changed the global entrypoint (before AND after taking the write lock).
**Invariant:** Termination argument: every iteration either returns a usable entrypoint or permanently denies one more node. A naive "retry N times" port either spins forever on a fully-dead graph or returns a spurious error — callers MUST map `errNoUsableEntrypoint` to empty results. The deny-list-contains-old-EP precondition is what prevents immediately re-selecting the corpse.
**Probe:** `grep -rn 'errNoUsableEntrypoint' adapters/repos/db/vector/hnsw/search_with_max_dist.go | head -2` → second caller mirrors the empty-result mapping; direct tests `delete_test.go::TestDelete_EntrypointIssues` (:1247), `TestDelete_MoreEntrypointIssues` (:1409).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "entrypointDistWithRepair repairGlobalEntrypoint no usable entrypoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the repair loop, the highest-level scan, and both race-outs. Adapt `handleDeletedDocOfNode`'s sibling logic to your id-space (single-vector stores can use plain `handleDeletedNode`). Omit metrics counters.
