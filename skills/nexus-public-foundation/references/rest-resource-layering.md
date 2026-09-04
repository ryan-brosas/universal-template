<!-- capsule-v2 -->
# REST resource layering — how do product REST endpoints stay thin: permission annotations, visibility filters, and status-code discipline?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d` (`nexus-scheduling/.../internal/resources/TasksApiResource.java`); Codebase Memory `nexus-public`. **Question:** What is the canonical shape of a v1 API resource — where do authz, not-found, conflict, and error mapping live relative to domain logic?

## JAX-RS resource = annotation-guarded adapter over the domain service
**Path/Symbol:** `public/common/components/nexus-scheduling/src/main/java/org/sonatype/nexus/scheduling/internal/resources/TasksApiResource.java` — class contract (:55–73), `getTasks` (:75–88), `run` (:100–122), `stop` (:124–147), `getTaskInfo` (:149–153).
**Signature:** `@Path(V1_API_PREFIX + "/tasks") @Produces/@Consumes(APPLICATION_JSON)`; every method carries `@RequiresAuthentication` + `@RequiresPermissions("nexus:tasks:<read|start|stop>")`; returns XO transfer objects (`TaskXO.fromTaskInfo`) wrapped in `Page<T>`.
**Data Shape:** list responses filter `isVisible()` config before mapping; stop uses `future.cancel(false)`; run requires enabled task else 405.

### Decisive source
```java
@Override
@POST
@Path("/{id}/stop")
@RequiresAuthentication
@RequiresPermissions("nexus:tasks:stop")
public void stop(@PathParam("id") final String id) {
  try {
    TaskInfo taskInfo = getTaskInfo(id);
    Future<?> taskFuture = taskInfo.getCurrentState().getFuture();
    if (taskFuture == null) {
      throw new WebApplicationException(format("Task %s is not running", id), CONFLICT);   // 409
    }
    if (!taskFuture.cancel(false)) {
      throw new WebApplicationException(format("Unable to stop task %s", id), CONFLICT);
    }
  }
  catch (WebApplicationException webApplicationException) { throw webApplicationException; } // rethrow OWN statuses
  catch (Exception e) {
    log.error("error stopping task with id {}", id, e);
    throw new WebApplicationException(format("Error stopping task %s", id), INTERNAL_SERVER_ERROR); // 500
  }
}

private TaskInfo getTaskInfo(final String id) {
  return ofNullable(taskScheduler.getTaskById(id))
      .filter(taskInfo -> taskInfo.getConfiguration().isVisible())
      .orElseThrow(() -> new NotFoundException("Unable to locate task with id " + id));   // 404
}
```

**Flow:** annotations enforce authn+authz BEFORE method entry (Shiro aspect). Lookup helper centralizes not-found + invisible-task filtering (hidden tasks are indistinguishable from missing ones — no existence oracle). Mutations translate domain outcomes to precise statuses: disabled task → 405 NotAllowed, not-running/failed-cancel → 409 CONFLICT, unexpected → 500 with logged cause. The resource never touches Quartz directly — only `TaskScheduler`.
**Invariant:** resources are adapters ONLY: no domain logic, no scheduler internals; XO mapping and Page wrapping at the boundary; own WebApplicationExceptions rethrown untouched so the catch-all can't mask them into 500s. Non-interrupting cancel(false) even from the API.
**Probe:** `nexus-scheduling/src/test/java/org/sonatype/nexus/scheduling/internal/resources/TasksApiResourceTest.java` — 13 test methods covering the status matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "TasksApiResource RequiresPermissions WebApplicationException CONFLICT isVisible", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the annotation-first guard pattern, invisible-equals-missing lookup helper, precise status ladder (405/409/404/500), and rethrow-own-exceptions discipline for any admin API surface. Adapt Shiro annotations and XO/Page types to your stack. Omit the ExtDirect (UI) twin layer — same domain, legacy transport.
