<!-- capsule-v2 -->
# Same-type task blocking (mayBlock) — how do you prevent two same-type tasks from interleaving without deadlocking, and when is a same-type task NOT a blocker?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-quartz/.../task/QuartzTaskJob.java`); Codebase Memory `nexus-public`. **Question:** How does a task wait for other RUNNING tasks of the SAME type to finish before starting — and why do blob-store tasks block only on the same blob store?

## Global-mutex state-transition loop with 1-minute bounded waits and per-blobstore refinement
**Path/Symbol:** `public/common/components/nexus-quartz/src/main/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskJob.java:mayBlock` (:197–249), `blockedBy` (:263–278), `isTrulyBlocking` (:285–292), `markTaskAsRunning` (:251–258).
**Signature:** `private void mayBlock() throws Exception` — called only after task instantiation and a not-cancelled check; `private boolean isTrulyBlocking(final TaskInfo otherTask)`.
**Data Shape:** blocker predicate = different id AND same typeId AND `state.isRunning()` AND runState not RUNNING_STARTING/RUNNING_BLOCKED AND truly-blocking. Static `Mutex MUTEX` shared by all job instances serializes every blocked/running transition.

### Decisive source
```java
synchronized (MUTEX) {
  blockedBy = blockedBy();
  if (blockedBy.isEmpty()) {
    markTaskAsRunning();                       // RUNNING + TaskStartedRunningEvent
    return;
  }
  TaskState previousRunState = taskFuture.getRunState();
  taskFuture.setRunState(RUNNING_BLOCKED);
  if (RUNNING_BLOCKED != previousRunState) {   // event only on real transition
    eventManager.post(new TaskBlockedEvent(taskInfo));
  }
}
// outside the lock: bounded wait per blocker
for (TaskInfo taskInfo : blockedBy) {
  Future<?> future = taskInfo.getCurrentState().getFuture();
  if (future != null) {
    future.get(1L, TimeUnit.MINUTES);          // TimeoutException => give up
  }
  if (taskFuture.isCancelled()) return;
}
...
catch (TimeoutException e) {
  throw new TaskInterruptedException("Blocked for too long, giving up", true);
}

private boolean isTrulyBlocking(final TaskInfo otherTask) {
  String blobStoreName = task.taskConfiguration().getString("blobstoreName");
  if (blobStoreName != null) {
    String otherBlobStoreName = otherTask.getConfiguration().getString("blobstoreName");
    return blobStoreName.equals(otherBlobStoreName);
  }
  return true;
}
```

**Flow:** loop { under global MUTEX: recompute blockers; none ⇒ mark RUNNING and return; else flip to RUNNING_BLOCKED (event once) } → wait each blocker's future with a 1-minute timeout → timeout throws cooperative-cancel `TaskInterruptedException`; blocker failure is ignored ("it will report itself"); cancellation during wait exits silently. The whole transition runs inside one mutex so two same-type tasks cannot both observe "no blockers".
**Invariant:** the run-state mutation is exclusive across ALL tasks (static mutex), but waiting happens OUTSIDE the lock — no deadlock. Blob-store tasks carry a `blobstoreName` config string: they only block same-type tasks on the SAME store; a non-blob-store task blocks everything of its type. Empty-vs-null blobstoreName asymmetry is pinned by tests.
**Probe:** `nexus-quartz/src/test/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskJobTest.java` — seven `testIsTrulyBlocking_*` cases (:99–178): same-store blocks, different stores don't, null-on-either-side ladder, empty-vs-populated doesn't block, different typeIds don't.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "mayBlock RUNNING_BLOCKED isTrulyBlocking blobstoreName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mutex-guarded blocker computation + bounded per-blocker future waits + the resource-scoping refinement (replace blobstoreName with your resource key). Adapt the event names and TaskInterruptedException semantics. Omit the FIXME'd IllegalStateException catch (upstream itself flags it as imprecise).
