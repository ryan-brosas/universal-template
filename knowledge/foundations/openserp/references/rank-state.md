<!-- capsule-v2 -->
# Rank state — how can ads and SERP features be emitted without shifting organic SEO ranks?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What counter discipline keeps organic rank stable when ads/PAA rows interleave, and what ordering makes mixed streams deterministic?

## Three counters, two rank spaces
**Path/Symbol:** `core/rank_state.go` (whole file, L1–54), `core/common.go:resultSortPosition/resultLess/resultDedupKey` (L218–252), `google/search.go` negative-rank usage (L412).
**Signature:** `NewRankState(pageNum) *RankState`; `NewRankStateAt(organicBase, absoluteBase)`; `(r) Next(isAd) (rank, absoluteRank int)`; `SetSeparatedAdAbsoluteRanks(results, start)`.
**Data Shape:** organicRank starts at pageNum*10, adRank restarts at 1 every page, absoluteRank counts EVERY row from start+1.

### Decisive source
```go
func (r *RankState) Next(isAd bool) (rank, absoluteRank int) {
	absoluteRank = r.absoluteRank
	r.absoluteRank++
	if isAd {
		rank = r.adRank; r.adRank++; return rank, absoluteRank
	}
	r.organicRank++; return r.organicRank, absoluteRank
}
// features that ride the result stream carry NEGATIVE internal ranks:
srchRes.Rank = -1 * (i + 1)            // google PAA rows
// sort: absolute first, then organic-before-ad, then rank, then URL
if leftPos != rightPos { return leftPos < rightPos }
if left.Ad != right.Ad { return left.Ad }   // false < true ⇒ organics first
```

**Flow:** browser parsers seed `NewRankStateAt(query.Start, query.Start+1)`; raw parsers seed `NewRankState(0)` then re-base by query.Start post-hoc (google/search_raw.go L216–230 shifts Rank and AbsoluteRank). Engines collecting ads in a separate pass (ecosia) call SetSeparatedAdAbsoluteRanks to synthesize one mixed order.
**Invariant:** organic Rank MUST NOT be shifted by ads (SEO callers plot position); dedup keys include ad/organic class so the same URL may appear once in each stream; sorting by AbsoluteRank restores on-page order regardless of emission order.
**Probe:** `go test ./core -run TestRankState` (pins page-1 seeding: ad→(1,11), organic→(11,12), interleaved ad→(2,14)); TestDeduplicateResultsKeepsAdAndOrganicForSameURL; TestEnvelopePaginationCountsOrganicResults.
**Probe executed (real runner):** all three named tests executed individually at pin = **1+1+1 PASS** (seeding matrix incl. interleaving, ad+organic same-URL dedupe keep-rule, organic-only pagination count).
**Python-equivalent probe (executed):**
```python
# re-derived the FSM in python and asserted the test's table:
steps = [(True,1,11),(False,11,12),(False,12,13),(True,2,14),(False,13,15)]
org,ad,abso = 10,1,10
out=[]
for isAd,wantR,wantA in steps:
    abso+=1
    if isAd: r=ad; ad+=1
    else: org+=1; r=org
    out.append((r,abso))
assert out==[(w[1],w[2]) for w in steps], out
print("rank-state FSM GREEN:", out)
```
→ executed GREEN (exact match incl. interleaved case).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "RankState Next AbsoluteRank resultLess DeduplicateResults", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the triple-counter scheme, the negative-rank feature convention, and absolute-then-ad-last ordering as-is; adapt the 10-per-page seeding constant to engines with different page sizes; omit SetSeparatedAdAbsoluteRanks unless you too collect streams separately.
