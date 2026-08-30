<!-- capsule-v2 -->
# HNSW filtered-search strategy FSM — which filter algorithm runs, and why a naive port picks the wrong one

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** When a filtered (allow-list) KNN search runs, which of the three strategies (SWEEPING / ACORN / RRE) executes, and what decides it?

## Strategy selection before layer search
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:38-44` (`FilterStrategy`), `:206-218` (`acornEnabled`), `:937-1008` (`knnSearchByVector` selection + seeding).
**Signature:** `acornEnabled(allowList helpers.AllowList) bool`; strategy chosen as local var in `knnSearchByVector`.
**Data Shape:** `allowList *helpers.AllowList` (nil = unfiltered); `h.acornSearch atomic.Bool` from user config `FilterStrategy == ent.FilterStrategyAcorn`; `h.acornFilterRatio float64`.

### Decisive source
```go
func (h *hnsw) acornEnabled(allowList helpers.AllowList) bool {
	if allowList == nil || !h.acornSearch.Load() { return false }
	cacheSize := h.cacheSize()
	allowListSize := allowList.Len()
	if cacheSize != 0 && float32(allowListSize)/float32(cacheSize) > float32(h.acornFilterRatio) {
		return false
	}
	return true
}
// ...in knnSearchByVector, after upper layers:
useAcorn := h.acornEnabled(allowList)
if useAcorn {
	if entryPointNode == nil { strategy = RRE } else {
		// count allowed neighbors of entrypoint at level 0
		if counter/float32(...LenAtLayer(0)) > float32(h.acornFilterRatio) { strategy = RRE } else { strategy = ACORN }
	}
} else { strategy = SWEEPING }
```

**Flow:** (1) nil allow-list ⇒ SWEEPING regardless (`searchLayerByVectorWithDistancerWithStrategy` also force-resets `strategy = SWEEPING` when `allowList == nil`, :290-292). (2) ACORN family only if user enabled `acornSearch` AND allow-list size ÷ cache size ≤ `acornFilterRatio`. (3) Within that: RRE ("restrict re-entry") when the entrypoint's level-0 neighborhood is mostly allowed (>ratio); ACORN ε-expansion otherwise. (4) If ACORN is active and allow-list non-nil, up to 10 live allow-list members are seeded as extra entrypoints (:978-1007).
**Invariant:** A porter who implements plain "filtered HNSW" without this gate changes recall/perf profile silently: SWEEPING tolerates sparse filters by walking everything; ACORN expands 2 hops past filtered-out neighbors to escape dead zones; RRE trusts the entrypoint's dense neighborhood. The ratio test must use `cacheSize()` (compressed ⇒ compressor count) — using node-slice length breaks under compression.
**Probe:** `grep -n 'func TestAcornPercentage' adapters/repos/db/vector/hnsw/search_test.go` → line 191; the test pins ratio behavior with `AcornFilterRatio: 0.4` and asserts a 50% allow-list disables acorn.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "searchLayerByVectorWithDistancerWithStrategy ACORN filter strategy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-strategy FSM and the ratio gates (both global pre-check and per-entrypoint neighborhood check). Adapt `cacheSize()` to your storage's count source. Omit the slow-query-log annotations (host observability).
