<!-- capsule-v2 -->
# ef resolution ladder — explicit ef, dynamic efWindow, and the k floor

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How is the search-time ef computed when the user sets ef = -1 (dynamic) vs an explicit value, and what clamps apply?

## searchTimeEF / autoEfFromK
**Path/Symbol:** `adapters/repos/db/vector/hnsw/search.go:46-78`.
**Signature:** `searchTimeEF(k int) int`; `autoEfFromK(k int) int`.
**Data Shape:** `h.ef`, `h.efMin`, `h.efMax`, `h.efFactor` all `int64` loaded atomically (concurrent user-config updates without locks); defaults from `ent.UserConfig` (DynamicEFMin=100, DynamicEFMax=500, DynamicEFFactor=8 in `entities/vectorindex/hnsw/config.go`).

### Decisive source
```go
func (h *hnsw) searchTimeEF(k int) int {
	ef := int(atomic.LoadInt64(&h.ef))
	if ef < 1 { return h.autoEfFromK(k) }   // -1 ⇒ dynamic
	if ef < k { ef = k }
	return ef
}
func (h *hnsw) autoEfFromK(k int) int {
	factor := int(atomic.LoadInt64(&h.efFactor))
	min := int(atomic.LoadInt64(&h.efMin)); max := int(atomic.LoadInt64(&h.efMax))
	ef := k * factor
	if ef > max { ef = max } else if ef < min { ef = min }
	if k > ef { ef = k }   // otherwise results will get cut off early
	return ef
}
```

**Flow:** explicit ef ≥ 1 is honored but floored at k. Dynamic mode multiplies k by factor then clamps into [min,max], with a FINAL floor of k that wins even over min — because a max-queue sized below k silently truncates results. The same resolved ef feeds both graph search (`knnSearchByVector`) and flat search over-fetch.
**Invariant:** The last `if k > ef` clamp must come AFTER the min/max clamp; reordering makes small-k searches return fewer than k results whenever min < k. Atomic loads (not mutex reads) are what allow hot ef updates under full query load — porting to plain reads introduces a data race on config updates.
**Probe:** `grep -rn 'DynamicEFMin' entities/vectorindex/hnsw/config.go | head -2` → default 100; direct test `entities/vectorindex/hnsw/config_test.go::Test_UserConfigFilterStrategy` (:1185) covers the config surface.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "searchTimeEF autoEfFromK dynamic ef window", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (explicit→floor-k; dynamic→factor→clamp[min,max]→floor-k). Adapt defaults to your product's. Omit atomics only if your config is immutable after start.
