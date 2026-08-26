<!-- capsule-v2 -->
# Quartz task future — what is the correct cancel ladder so cooperative tasks are never thread-interrupted unless the caller insists?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-quartz/.../task/QuartzTaskFuture.java`); Codebase Memory `nexus-public`. **Question:** How do I wrap a Quartz job execution in a `Future` whose cancel prefers Quartz's own un-schedule path and only falls back to thread interruption when explicitly asked — while keeping run-state transitions legal?

## Cancel-ladder Future with monotonic run-state guard
**Path/Symbol:** `public/common/components/nexus-quartz/src/main/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskFuture.java:cancel` (:130–153), `doCancel` (:155–164), `setRunState` (:121–127).
**Signature:** `public boolean cancel(final boolean mayInterruptIfRunning)` (Future override); `void setRunState(final TaskState runState)`; `void doCancel()`; completion signaled by `CountDownLatch countDownLatch = new CountDownLatch(1)`.
**Data Shape:** `jobExecutingThread` and `runState` are `volatile`; starts at `RUNNING_STARTING`; `isDone()` == latch count 0; `isCancelled()` == `runState == RUNNING_CANCELED`.

### Decisive source
```java
@Override
public boolean cancel(final boolean mayInterruptIfRunning) {
  boolean canceled = scheduler.cancelJob(jobKey);      // 1. try Quartz-native unschedule
  Thread thread = this.jobExecutingThread;

  if (!canceled && thread != null && mayInterruptIfRunning) {
    // Yell about this, as this is dangerous
    log.info("Task cancelling w/ interruption {}", taskLogName);
    thread.interrupt();                                 // 2. only if caller insisted
    canceled = true;
  }

  if (canceled || runState == RUNNING_STARTING) {       // 3. not-yet-started also cancels
    doCancel();
  }
  return canceled;
}

public void setRunState(final TaskState runState) {
  checkState(runState.isRunning() && this.runState.ordinal() <= runState.ordinal(),
      "Illegal run state transition: %s -> %s", this.runState, runState);
  this.runState = runState;
}
```

**Flow:** cancel tries `scheduler.cancelJob(jobKey)` first (removes future firings; Quartz marks the execution interrupted cooperatively). Only when that returns false AND a live executing thread exists AND the caller passed `true` does it call `thread.interrupt()`. `doCancel()` flips state to RUNNING_CANCELED then releases the latch with a CancellationException result.
**Invariant:** run-state transitions are strictly forward (`ordinal()` non-decreasing) among running states — enforced by `checkState`, so a late `setRunState(RUNNING)` after cancel fails loudly instead of resurrecting the task. Interruption is opt-in per call, never a default.
**Probe:** `nexus-quartz/src/test/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskJobTest.java` exercises the surrounding job/future contract; cancel semantics pinned indirectly through scheduler tests. Coverage caveat: no dedicated `QuartzTaskFutureTest` upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "QuartzTaskFuture cancelJob mayInterruptIfRunning RUNNING_STARTING", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-step cancel order (native un-schedule → optional interrupt → starting-state catch-up) and the ordinal-guarded monotonic transitions. Adapt TaskState enum values to your host. Omit the Quartz JobKey coupling if your scheduler has a different native-cancel primitive.
