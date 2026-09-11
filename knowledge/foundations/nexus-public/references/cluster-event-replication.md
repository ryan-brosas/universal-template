<!-- capsule-v2 -->
# Cluster event replication — how do multiple nodes sharing one job store keep each other's schedulers in sync without a custom transport?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-quartz/.../datastore/DatastoreQuartzSchedulerSPI.java`); Codebase Memory `nexus-public`. **Question:** When node A schedules a task and the Quartz JDBC store is shared, how does node B learn to attach its listener and fire the job — and how does cancel propagate cross-node?

## Self-addressed Job/Trigger events replayed as native Quartz signals
**Path/Symbol:** `public/common/components/nexus-quartz/src/main/java/org/sonatype/nexus/quartz/internal/datastore/DatastoreQuartzSchedulerSPI.java` — event emission (:84–234), remote handling `@Subscribe on(JobCreatedEvent)` (:244–252), trigger twins (:295–342), cancel relay (:106–119, :236–242).
**Signature:** `extends QuartzSchedulerSPI implements EventAware`; every mutation method posts `{Job,Trigger}{Created,Updated,Deleted}Event(key)` unless `EventHelper.isReplicating()`; handlers act only when `isReplicating()` (i.e., the event came from ANOTHER node).
**Data Shape:** events carry just the key (`JobKey`/`TriggerKey`) + remote node id — receivers re-fetch full state from the shared store.

### Decisive source
```java
@Subscribe
public void on(final JobCreatedEvent event) {
  handle(event, jobDetail -> {
    attachJobListener(jobDetail.getKey());
    // simulate signals Quartz would have sent
    quartzScheduler.getSchedulerSignaler().signalSchedulingChange(0L);
    quartzScheduler.notifySchedulerListenersJobAdded(jobDetail);
  });
}

@Guarded(by = STARTED)
@Override
public boolean cancel(final String id, final boolean mayInterruptIfRunning) {
  boolean locallyCancelled = super.cancel(id, mayInterruptIfRunning);
  if (locallyCancelled) return true;
  if (!EventHelper.isReplicating()) {
    eventManager.post(new CancelJobEvent(id, mayInterruptIfRunning));
  }
  return false;
}
```

**Flow:** local mutation → post domain event (suppressed when already replicating, so remote echoes never re-post). Every peer receives it while `isReplicating()` is true → looks the entity up in the SHARED store → attaches/removes its per-job listener → then manually replays the internal signals Quartz would have fired locally (`signalSchedulingChange(0L or nextFireMillis)` + `notifySchedulerListeners*`). Run-now triggers created elsewhere get an immediate `signalSchedulingChange(0L)` ping if limited to this node. Local-cancel-miss falls back to broadcasting `CancelJobEvent`, handled only by peers.
**Invariant:** the `isReplicating()` guard makes the event bus loop-safe: originators post, receivers consume without re-broadcasting. All handler work happens under a mutex with TCCL block, and missing entities are logged-and-skipped (shared-store races are expected). No custom wire protocol — the shared DB + simulated Quartz signals ARE the transport.
**Probe:** `nexus-quartz/src/test/java/org/sonatype/nexus/quartz/internal/datastore/DatastoreQuartzSchedulerSPITest.java` pins listener attach/update behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "JobCreatedEvent signalSchedulingChange notifySchedulerListenersJobAdded isReplicating", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt emit-suppress/receive-guard event replication and "replay your engine's own signals instead of inventing a sync protocol" for any shared-store scheduler. Adapt the event bus to yours (NATS/Kafka/etc.) keeping keys-only payloads. Omit OrientDB-era DAO specifics.
