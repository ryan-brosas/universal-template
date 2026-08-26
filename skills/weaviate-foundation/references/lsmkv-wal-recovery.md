<!-- capsule-v2 -->
# WAL crash recovery — newest WAL becomes the memtable, older WALs flush to segments, corruption is tolerated

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** At bucket open, how are leftover .wal files replayed, and what happens to a torn tail?

## mayRecoverFromCommitLogs
**Path/Symbol:** `adapters/repos/db/lsmkv/bucket_recover_from_wal.go:34-262`.
**Signature:** `mayRecoverFromCommitLogs(ctx, sg *SegmentGroup, files map[string]int64) error`.
**Data Shape:** WAL names `segment-<unix-nano>.wal` — fixed width so lexicographic sort == chronological (source map iteration order is random; sort is mandatory); empty WALs deleted outright.

### Decisive source
```go
sort.Strings(walFileNames)
for i, fname := range walFileNames {
    walForActiveMemtable := i == len(walFileNames)-1     // only the LAST becomes live state
    ...
    errRecovery := newCommitLoggerParser(strategy, bufio.NewReaderSize(meteredReader, 32*1024), mt).Do()
    if errRecovery != nil {
        log "write-ahead-log ended abruptly, some elements may not have been recovered"
    }
    if walForActiveMemtable && errRecovery == nil {
        b.active = mt                                     // healthy newest WAL: keep as memtable
    } else {
        // damaged OR older-than-newest: flush to a segment so nothing is lost
        segmentPath, err := mt.flush()
        if mt.Size() > 0 { sg.add(segmentPath) }
    }
}
if recovered { sort.Slice(sg.segments, byPath) }          // force re-order after adds
```
Context policy: checked ONCE up-front — an in-flight recovery always completes because in a crashloop each restart recovers one more bucket until startup fits.

**Flow:** collect non-empty `.wal` files → chronological sort → replay each into a fresh memtable via the strategy-specific parser (replace/collection/roaringset/roaringsetrange/inverted) → the newest healthy WAL's memtable becomes `b.active`; every other (or damaged) WAL's contents are flushed into disk segments added to the group. A torn record stream logs loudly but keeps everything before the tear.
**Invariant:** The "last WAL = active memtable, rest = flush" rule REQUIRES the sort; iterating the map directly would randomly pick which WAL survives as memory state. A corrupted ACTIVE wal must NOT become the memtable (its bytes can't be trusted for future appends) — flushing it converts partial data into durable segment data instead.
**Probe:** direct tests `lsmkv/bucket_recover_test.go::TestBucketWalReload/TestBucketRecovery/TestBucketReloadAfterWalDamange` (:28/:182/:271) and integration `recover_from_wal_order_integration_test.go::TestReplaceStrategy_RecoverFromMultipleWALs_NewestWins` (:32).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "mayRecoverFromCommitLogs WAL recovery memtable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sort-then-replay with newest-becomes-active. Adapt naming/parsing to your WAL format. Omit edit-ops sidecar interplay unless porting drop-vector bookkeeping too.
