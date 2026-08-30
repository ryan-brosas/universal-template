<!-- capsule-v2 -->
# Capability registry HA sync — how do you replicate CRUD of in-memory plugin instances across cluster nodes without deadlocking on your own RW lock?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-core/.../internal/capability/DefaultCapabilityRegistry.java`); Codebase Memory `nexus-public`. **Question:** How do you keep a registry of live objects (each running lifecycle callbacks) in sync with a shared database when other nodes mutate it concurrently — without event handlers deadlocking against the registry lock?

## Storage events drive convergence; handlers submit to a single-thread executor; workers re-read the DB as truth
**Path/Symbol:** `public/common/components/nexus-core/src/main/java/org/sonatype/nexus/internal/capability/DefaultCapabilityRegistry.java` — `capabilitySyncExecutor` + rationale comment (:119–124), `doStart/doStop` (:152–180), `@Subscribe on(Created/Updated/DeletedEvent)` (:248–257, :342–351, :427–436), `processRemoteCapabilityEvent` (:691–724), `syncCapabilityReference` (:726–745), idempotence guards `capabilityAlreadyRegistered` (:259–265) and `capabilityAlreadyUpToDate` (:267–273).
**Signature:** `private void processRemoteCapabilityEvent(final CapabilityIdentity id)` — runs under the write lock but ONLY from the dedicated executor; `ExecutorService capabilitySyncExecutor = Executors.newSingleThreadExecutor(new NexusThreadFactory("capability-sync", ...))`.
**Data Shape:** `references: ConcurrentHashMap<CapabilityIdentity, DefaultCapabilityReference>` behind `ReentrantReadWriteLock`; storage items carry `(version, type, enabled, notes, properties)`. Events are `!event.isLocal()` filtered.

### Decisive source
```java
/**
 * Single-threaded executor for processing remote capability events sequentially.
 * This eliminates deadlock risk by ensuring event handlers never hold locks.
 */
private ExecutorService capabilitySyncExecutor;

@Subscribe
public void on(final CapabilityStorageItemCreatedEvent event) {
  if (!event.isLocal()) {                       // own writes converge via the local path already
    capabilitySyncExecutor.submit(() -> processRemoteCapabilityEvent(id));
  }
}

private void processRemoteCapabilityEvent(final CapabilityIdentity id) {
  lock.writeLock().lock();                      // blocking lock is safe: dedicated thread
  try {
    CapabilityStorageItem item = capabilityStorage.read(entityId(id)).orElse(null);
    if (item == null) {                         // deleted remotely ⇒ remove locally if present
      if (references.containsKey(id)) { doRemove(id); }
      return;
    }
    if (capabilityAlreadyUpToDate(id, item)) { return; }   // skip no-op syncs
    ...
    syncCapabilityReference(id, item, descriptor, type);   // doAdd or doUpdate
  } finally { lock.writeLock().unlock(); }
}
```

**Flow:** every local mutation writes to shared storage FIRST; the storage layer emits Created/Updated/Deleted events → remote nodes' handlers ignore local events, submit the id to the single-thread executor → worker takes the write lock, RE-READS the item from storage (the event payload is not trusted), then either removes (gone), skips (identical type+properties+enabled), creates (unknown id), or updates (changed) — update order inside `doUpdate`: disable-if-turning-off BEFORE reference.update, enable+activate AFTER (:353–374).
**Invariant:** (1) Event handlers NEVER take the lock — they only submit; the single thread makes remote events apply in-order and lets the worker safely use the BLOCKING write lock (no re-entrancy surprise from an event bus thread that might already hold read locks). (2) The database, not the event, is the source of truth at processing time — late/duplicate/out-of-order events converge because state is re-fetched. (3) Syncs are idempotent (`alreadyUpToDate`) so event replays are harmless. (4) Local-node latency trick: the writer applies its change in-memory synchronously under the same lock; remote application is eventually-consistent. (5) Unknown capability types on load are skipped with an INFO log, never fatal (`load()` :520–526) — pinned by `loadWhenCapabilityIsNotUnique` which expects BOTH duplicates to load with no failure.
**Probe:** `nexus-core/src/test/java/org/sonatype/nexus/internal/capability/DefaultCapabilityRegistryTest.java` — `testCapabilityAlreadyRegistered` (:838), `testCapabilityAlreadyUpToDate` (:859) + `_withDifferentProperties` (:880), `refreshReferencesOnDemand` (:587–628: manual pull-and-refresh converges properties while keeping secrets encrypted), `loadWhenCapabilityIsNotUnique` (:552–573).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "processRemoteCapabilityEvent capabilitySyncExecutor CapabilityStorageItemCreatedEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape: storage-first writes + remote-event notifications + single-thread applier that re-reads authoritative state under a blocking lock, with explicit up-to-date short-circuits. Adapt the transport (any pub/sub over your shared store) and the entityId mapping. Omit OrientDB/MyBatis storage specifics and the legacy `pullAndRefreshReferencesFromDB` full-scan fallback (kept for HA edge cases).
