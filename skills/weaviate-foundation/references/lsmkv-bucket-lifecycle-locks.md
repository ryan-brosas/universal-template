<!-- capsule-v2 -->
# Bucket lifecycle locks — double-open refusal, lifetimeLock drain-before-free, shutdown ordering

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does a bucket prevent double-open data loss and SEGFAULT-on-shutdown while readers hold mmap'd segments?

## NewBucket claim-first + Shutdown drain
**Path/Symbol:** `adapters/repos/db/lsmkv/bucket.go:304-337` (`NewBucket` registry claim), `:98-102` (lock-order doc), `:1860-1977` (`Shutdown`).
**Signature:** `NewBucket(ctx, dir, rootDir string, logger, metrics, compactionCallbacks, flushCallbacks, opts...)`.
**Data Shape:** `GlobalBucketRegistry` keyed by dir path; lock order: `lifetimeLock` OUTER → `flushAndSwitchMu` → `flushLock` INNER.

### Decisive source
```go
// Claim the registry entry BEFORE touching any file: a second open of a still-live
// bucket ... must be refused up front. Checking last let a doomed re-open run WAL
// recovery first — deleting the live instance's active WAL, whose buffered writes
// then flushed into an unlinked inode on shutdown: silent data loss.
if err := GlobalBucketRegistry.TryAdd(dir); err != nil { return nil, err }
defer func() { // on failure AFTER disk init: tear down mmapped segments+flocked handles;
    if teardown fails { KEEP the claim — re-open stays refused until restart }
}()
...
func (b *Bucket) Shutdown(ctx context.Context) (err error) {
    b.shuttingDown.Store(true)
    b.flushAndSwitchMu.Lock(); b.flushAndSwitchMu.Unlock()   // barrier: wait out mid-flight edit-op arms
    drained := make(chan struct{})
    go heartbeat ticker 30s "still draining in-flight read pins"   // diagnosable wedge
    b.lifetimeLock.Lock()                                    // drains ALL read pins; no timeout:
    close(drained)                                           // timeout-then-free would SEGFAULT a reader
    defer b.lifetimeLock.Unlock()
    if err == nil { GlobalBucketRegistry.Remove(b.registeredPath) }  // release ONLY on completed teardown
}
```

**Flow:** open claims the directory in a global registry BEFORE any IO so a leaked previous instance makes re-open fail fast instead of racing its WAL; failed constructions tear down partial state and keep the claim if teardown itself failed. Shutdown flips `shuttingDown` (new edit-ops hard-fail), barriers against in-flight flush/edit arms, then takes lifetimeLock write-side to drain every pinned reader BEFORE freeing mmap'd segments, then flushes active memtable (reusing WAL when small), waits out a concurrent flush, and releases the registry claim only on success.
**Invariant:** Never free segment mappings while any lifetimeLock.RLock holder exists — hence no drain timeout. Releasing the registry claim on FAILED shutdown invites a second open over live handles (the exact bug class the front claim kills). The empty critical section used as a barrier is deliberate (`//nolint:staticcheck`).
**Probe:** `grep -n 'GlobalBucketRegistry.TryAdd\|GlobalBucketRegistry.Remove' adapters/repos/db/lsmkv/bucket.go` → :316 and :1895; behavior covered by `TestBucket*` suite (bucket_test.go :70+) and shutdown integration tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "NewBucket GlobalBucketRegistry lifetimeLock shutdown drain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt claim-first-open, drain-before-free with heartbeat, and claim-release-only-on-success. Adapt the registry to your shard manager. Omit metrics.
