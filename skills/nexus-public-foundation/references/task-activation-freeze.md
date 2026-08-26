<!-- capsule-v2 -->
# Task activation freeze — how does a scheduler pause for maintenance without losing queued work, and which tasks survive?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-scheduling/.../internal/TaskActivation.java`); Codebase Memory `nexus-public`. **Question:** How do I implement scheduler freeze/pause so upgrades can block task execution while keeping the schedule durable — and let a few critical tasks opt out of being cancelled?

## Freeze-aware lifecycle wrapper around SchedulerSPI
**Path/Symbol:** `public/common/components/nexus-scheduling/src/main/java/org/sonatype/nexus/scheduling/internal/TaskActivation.java:doStart` (:58–62), `freeze` (:75–85), `cancelOnFreeze` (:87–90), `maybeCancel` (:100–103).
**Signature:** `public class TaskActivation extends StateGuardLifecycleSupport implements Freezable`; ctor takes `SchedulerSPI scheduler`.
**Data Shape:** `frozen` is `volatile boolean` — no lock; correctness comes from ordering pause/resume against lifecycle state, not mutual exclusion. Lifecycle phase `TASKS`, started last in phase via `@Priority(Integer.MIN_VALUE)`.

### Decisive source
```java
@Override
public void freeze() {
  frozen = true;
  if (isStarted()) {
    scheduler.pause();
    scheduler.listsTasks()
        .stream()
        .filter(this::cancelOnFreeze)          // drop tasks with RUN_WHEN_FROZEN=true
        .filter(taskInfo -> !maybeCancel(taskInfo))
        .forEach(taskInfo -> log.warn("Unable to cancel task: {}", taskInfo.getName()));
  }
}

private boolean cancelOnFreeze(final TaskInfo taskInfo) {
  return taskInfo.getConfiguration() == null
      || !taskInfo.getConfiguration().getBoolean(TaskConfiguration.RUN_WHEN_FROZEN, false);
}

private boolean maybeCancel(final TaskInfo taskInfo) {
  Future<?> future = taskInfo.getCurrentState().getFuture();
  return future == null || future.cancel(false);   // never interrupt running work
}
```

**Flow:** `freeze()` sets flag → pauses scheduler (no NEW fires) → filters out tasks whose config carries `RUN_WHEN_FROZEN=true` → cancels the rest via `future.cancel(false)` (running tasks finish naturally). `unfreeze()` clears the flag and resumes only if started. `doStart()` respects the flag: a node booting while frozen never resumes.
**Invariant:** freeze cancels are always non-interrupting; the schedule itself is durable in Quartz's job store, so pausing loses nothing — only firing stops. A task that must run during maintenance declares `RUN_WHEN_FROZEN=true` in its configuration; everything else yields.
**Probe:** `nexus-scheduling/src/test/java/org/sonatype/nexus/scheduling/internal/TaskActivationTest.java` — `testPauseScheduler_cancelTasksOnFreeze` (:77), `testRestartScheduler_onUnfreeze` (:91), `testSchedulerNotResumed_onFrozenStartup` (:109).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "TaskActivation freeze unfreeze RUN_WHEN_FROZEN", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the volatile-flag + pause/cancel(false)/resume ladder and the per-task freeze exemption key for any maintenance-mode scheduler. Adapt the Spring `@ManagedLifecycle`/phase wiring to your host's lifecycle hooks. Omit the StateGuard base class specifics. Direct-test probes verified on-disk this pass.
