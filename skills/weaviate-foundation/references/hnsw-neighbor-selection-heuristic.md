<!-- capsule-v2 -->
# Neighbor selection heuristic — diversity filter with compressed-bag fast path

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How are candidate neighbors pruned to M diverse links (Algorithm 4 of HNSW), and what changes when vectors are compressed?

## selectNeighborsHeuristic
**Path/Symbol:** `adapters/repos/db/vector/hnsw/heuristic.go:23-148`.
**Signature:** `selectNeighborsHeuristic(input *priorityqueue.Queue[any], max int, denyList helpers.AllowList) error` — mutates `input` in place to keep only accepted items.
**Data Shape:** internal min-queue ordered closest-first with insertion index (`InsertWithValue`); uncompressed path fetches ALL candidate vectors once via `h.multiVectorForID(ctx, ids)` (positional `curr.Value` indexes into that slice); compressed path builds one `compressor.NewBag()`, loads each id, then measures peer distances via `bag.Distance(curr.ID, item.ID)`.

### Decisive source
```go
if input.Len() < max { return nil }              // fewer candidates than slots ⇒ nothing to do
for input.Len() > 0 { elem := input.Pop(); closestFirst.InsertWithValue(elem.ID, elem.Dist, i); ids[i] = elem.ID; i++ }
for closestFirst.Len() > 0 && len(returnList) < max {
    curr := closestFirst.Pop()
    if denyList != nil && denyList.Contains(curr.ID) { continue }
    distToQuery := curr.Dist
    good := true
    for _, item := range returnList {
        peerDist, err := bag.Distance(curr.ID, item.ID)   // compressed; SingleDist(vecs[...]) otherwise
        if err != nil {
            var e storobj.ErrNotFound
            if errors.As(err, &e) { continue }            // deleted mid-heuristic ⇒ skip PAIR, not candidate
            return err
        }
        if peerDist < distToQuery { good = false; break } // closer to an already-picked neighbor than to the query ⇒ drop
    }
    if good { returnList = append(returnList, curr) }
}
for _, retElem := range returnList { input.Insert(retElem.ID, retElem.Dist) }  // write back
```

**Flow:** early-exit when under budget → sort candidates closest-first → greedily accept a candidate iff no already-accepted neighbor is closer to it than the query is (diversity/dispersal test) → stop at `max` → splice survivors back into the caller's queue. Deleted-in-store members degrade gracefully: ErrNotFound skips only the pairwise comparison.
**Invariant:** The heuristic MUTATES its input queue in place (drains then refills) — callers like `doAtLevel` rely on reading survivors afterward; a port that returns a fresh queue while callers read the original silently keeps ALL candidates. The `input.Len() < max` early return is behavior, not optimization: it preserves all candidates including deny-listed extras handled elsewhere.
**Probe:** `grep -n 'func (h \*hnsw) selectNeighborsHeuristic' adapters/repos/db/vector/hnsw/heuristic.go` → :23; exercised by every tombstone-reassignment test via `reconnectNeighboursOf` (delete_test.go :153+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "selectNeighborsHeuristic diversity peer distance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the greedy diversity test and in-place mutation contract. Adapt the compressed `bag` abstraction to your quantizer's pairwise-distance API. Omit pool churn details.
