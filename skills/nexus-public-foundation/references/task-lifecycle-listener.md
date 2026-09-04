<!-- capsule-v2 -->
# Task lifecycle listener — who owns the RUNNING→WAITING/DONE state machine and persists last-run results into durable job data?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-quartz/.../task/QuartzTaskJobListener.java`); Codebase Memory `nexus-public`. **Question:** Where exactly does a task's end state (OK/FAILED/CANCELED) get recorded so it survives restarts, and why must the future result be set BEFORE the task-info update?

## Per-job-listener stateful execution bookkeeping
**Path/Symbol:** `public/common/components/nexus-quartz/src/main/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskJobListener.java:jobToBeExecuted` (:83–119), `jobWasExecuted` (:122–193).
**Signature:** `implements JobListener`; one listener instance per jobKey — safe to hold `taskInfo` as a field because Nexus jobs are `@DisallowConcurrentExecution` ("unique per jobKey").
**Data Shape:** end-state derivation: cancelled→CANCELED, else JobExecutionException→FAILED, else OK; next-state = `!removedOrDone && nextFireTime != null ? WAITING : DONE`.

### Decisive source
```java
// jobWasExecuted — the ordering IS the invariant
final TaskConfiguration taskConfiguration = configurationOf(context.getJobDetail());
long runDuration = System.currentTimeMillis() - future.getStartedAt().getTime();
taskConfiguration.setLastRunState(endState, future.getStartedAt(), runDuration);
updateJobData(context.getJobDetail(), taskConfiguration);   // persist last-run INTO job data
...
future.setResult(context.getResult(), failure);   // MUST happen first…

taskInfo.setNexusTaskState(                        // …because this can REMOVE the task,
    state,                                         // and a removed+unset future reads CANCELED
    new QuartzTaskState(taskConfiguration, jobSchedule, nextFireTime),
    state.isDone() ? future : null);
```

**Flow:** on start (`jobToBeExecuted`) the listener lazily creates a `QuartzTaskFuture`, stashes future + taskInfo into the JobExecutionContext (the hand-off channel to the prototype-scoped job), sets task state RUNNING, posts `TaskEventStarted`. On end it computes endState from cancel/exception, writes lastRunState + duration into the configuration, flushes via `updateJobData`, unwraps the Quartz-wrapped exception (`jobException.getCause()`), sets the future result, THEN updates task state to WAITING (drop future) or DONE (keep future).
**Invariant:** `setResult` strictly precedes `setNexusTaskState(DONE)` — the comment says it outright: "This might result in task removal, so we MUST set result as above BEFORE this, otherwise task will be CANCELLED". LastRunState lives in persisted job data, not memory, which is how the UI shows the previous outcome after a crash.
**Probe:** `nexus-quartz/src/test/java/org/sonatype/nexus/quartz/internal/task/QuartzTaskJobTest.java` + `datastore/DatastoreQuartzSchedulerSPITest.java` cover listener attach/update paths; end-state matrix pinned at mock level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "jobWasExecuted setLastRunState WAITING isRemovedOrDone", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the listener-owned state machine and the result-before-removal ordering; adopt "persist last outcome into the durable job record" for any scheduler with a UI. Adapt event classes (TaskEventStoppedDone/Failed/Canceled) to your bus. Omit Quartz Trigger conversion details.
