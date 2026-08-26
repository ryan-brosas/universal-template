<!-- capsule-v2 -->
# Level-pair compaction candidate selection — descending-level invariant, size limits, level-order repair

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** Which two segments merge next in an LSM segment group, and how are corrupted level orders healed?

## findCompactionCandidates
**Path/Symbol:** `adapters/repos/db/lsmkv/segment_group_compaction.go:60-224` (`findCompactionCandidates`), `:226+` (`isSimilarSegmentSizes`: within factor ~4× above 1GiB), `:294-333` (`compactOnce`/`watchAbort`).
**Signature:** `findCompactionCandidates() (pair []int, level uint16)` — nil pair = nothing to do.
**Data Shape:** `sg.segments` ordered newest→oldest by creation; each has `level uint16` (times compacted); options `maxSegmentSize int64`, `compactLeftOverSegments bool`, `keepLevelCompaction bool`.

### Decisive source
```go
if sg.isReadyOnly() { return nil, 0 }            // shard READONLY halts compaction
if len(sg.segments) < 2 { return nil, 0 }
// loop segments NEWEST-first (reverse):
for i := len(sg.segments)-2; i >= 0; i-- {
    lLvl, rLvl := seg[i].level, seg[i+1].level
    if lLvl < rLvl { isUnordered = true; break }             // levels must descend toward older
    if lLvl == rLvl && fitsSizeLimit {
        matchingPairFound = true; matchingPos = i
        matchingLvl = lLvl + 1                                // merged segment rises one level...
        if keepLevelCompaction { matchingLvl = lLvl }         // ...unless migration keeps levels flat
        // but if an OLDER segment shares this level, keep lLvl so old never gets "passed"
    } else if lLvl != rLvl && compactLeftOverSegments && fitsSizeLimit && similarSizes {
        leftoverPairFound = true                              // escape hatch: unequal levels, similar sizes
    }
}
// unordered repair pass: merge the offending left neighbor into the last-ordered run,
// keeping the right side's level, until descending order is restored (lazy healing)
```

**Flow:** pick the NEWEST same-level pair first (prioritizes absorbing fresh writes early), assign merged level = pair level+1 unless an even older segment sits at that level (then stay put — never let a new segment outrank older ones), fall back to size-similar cross-level pairs when allowed, else heal out-of-order levels lazily. Only CONSECUTIVE segments ever merge, preserving write ordering. Doc comment carries worked examples (s4+s5→(3) before s2+s3→(4)).
**Invariant:** The descending-toward-older level order is the correctness core: merging non-consecutive segments reorders creations/updates/deletes and corrupts replace semantics. The "keep level when older sibling exists" rule prevents a merged segment from jumping the queue past data it must lose to. Size-limit exemption for unordered repairs is deliberate (comment :100).
**Probe:** direct tests pin the exact examples: `segment_group_compaction_test.go::TestSegmentGroup_BestCompactionPair` (:33), `TestSegmentGroup_CompactionPairToFixLevelsOrder` (:99), plus 12 `TestSegmentGroup_CompactionCandidates_*` matrices (:1434-3593).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "findCompactionCandidates segment level pair", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt candidate scoring incl. lazy level repair. Adapt `isSimilarSegmentSizes` thresholds. Omit metrics/stats plumbing.
