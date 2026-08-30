<!-- capsule-v2 -->
# FlushAndSwitch four-phase non-blocking flush — leftover-drain, writer drain, tombstone fan-out race

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does a memtable flush stay non-blocking for readers/writers while guaranteeing no acknowledged write is ever lost?

## Four phases + serialization mutex
**Path/Symbol:** `adapters/repos/db/lsmkv/bucket.go:85-122` (lock docs), `:1984-2038` (`flushAndSwitchIfThresholdsMet`: memtable ≥ threshold OR wal ≥ threshold OR dirty ≥ 60s; READONLY halt w/ backoff timer), `:2125-2291` (`FlushAndSwitch`→`flushAndSwitchLocked`→`flushFlushingLocked`), `:2297-2392` (`atomicallySwitchMemtable`, `atomicallyAddDiskSegmentAndRemoveFlushing`).
**Signature:** `FlushAndSwitch() error`; `atomicallySwitchMemtable(createNewActiveMemtable func() (memtable, error)) (bool, error)`.
**Data Shape:** locks: `flushAndSwitchMu` (serializes flushers) OUTER, `flushLock` RWMutex INNER (pointer swaps), `lifetimeLock` outermost for shutdown; thresholds: memtableThreshold 10MB, walThreshold 1GB, flushDirtyAfter 60s.

### Decisive source
```go
// phase 0: a non-nil b.flushing is the aftermath of a FAILED earlier flush.
// Switching over it would orphan its acknowledged writes until restart WAL-replay.
if b.flushing != nil { retry it first via flushFlushingLocked() }
// phase 1 (fast, blocking): swap pointers under flushLock
flushing := b.active; b.active = mt(new); b.flushing = flushing
// refuses to overwrite a leftover: "previous flushing memtable still present"
// phase 2+3 (slow, background): waitForZeroWriters(b.flushing) then mt.flush()
//   then disk.initAndPrecomputeNewSegment(segmentPath) under maintenanceLock.RLock
// phase 4 (fast, blocking): addInitializedSegment + b.flushing = nil under flushLock
// StrategyInverted only: fan the flushed memtable's tombstones out to ALL segments:
for _, seg := range segments { seg.MergeTombstones(tombstones) }
// accepted race (comment #9104): compaction may drop freshly merged tombstones ⇒
// deleted objects briefly reappear in scoring; self-heals on restart. Non-critical by design.
```

**Flow:** threshold check runs on the periodic flush callback; read-only shards halt with an exponentially backing-off warn timer. Real flush: switch (O(1)) → wait for in-flight writers to drain to zero (100ms ticker with warning after 1s) → write segment → precompute bloom filters/net-counts while segment group is frozen by maintenanceLock.RLock → atomic append + clear flushing → inverted-strategy tombstone fan-out.
**Invariant:** Lock ORDER `flushAndSwitchMu → flushLock` is documented as deadlock-critical (reverse order hangs). The empty-memtable early return inside `atomicallySwitchMemtable` was once racy with concurrent callers — hence the serializer whose whole reason is GH issue #212 C+D: "after FlushAndSwitch returns, all data written before the call is durably in segments". Never delete the flushing pointer before the segment is added.
**Probe:** `grep -c 'flushAndSwitchMu' adapters/repos/db/lsmkv/bucket.go` → 15; direct test `bucket_test.go::TestBucket_MemtableCountWithFlushing` (:242).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "FlushAndSwitch atomicallySwitchMemtable flush memtable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-phase split, serializer mutex, and leftover-flush drain. Adapt thresholds and writer-refcount mechanics to your engine. Omit prometheus timers.
