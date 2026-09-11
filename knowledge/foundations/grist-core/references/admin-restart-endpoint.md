<!-- capsule-v2 -->
# Graceful self-restart endpoint — how does a server apply env changes by restarting itself without dropping the response?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** An admin hits POST /api/admin/restart — what is the exact choreography between HTTP response, readiness flag, and supervisor IPC?

## Respond first, flip ready=false, THEN ask the parent to restart on 'finish'; 409 when restart is unavailable
**Path/Symbol:** `app/server/lib/attachEarlyEndpoints.ts:104-137` (`/api/admin/restart`); capability check `canRestart()` from `adminPageConfig`; readiness switch `gristServer.setReady(false)`.
**Signature:** handler inside `expressWrap`; side effects keyed off `res.on("finish")`.
**Data Shape:** success `{ msg: "ok" }` (200); refusal `{ error, details: { code: "RestartUnavailable" } }` (409).

### Decisive source
```ts
res.on("finish", () => {
  // If we have IPC with parent process (e.g. when running under Docker) tell
  // the parent that we have a new environment so it can restart us.
  if (process.send && canRestart()) {
    process.send({ action: "restart" });
  }
});
if (!canRestart()) {
  // "409: This response is sent when a request conflicts with the current state of the server."
  return res.status(409).send({ error: "...Please restart server manually.",
    details: { code: "RestartUnavailable" } satisfies ApiErrorDetails });
}
// We're going down, so we're no longer ready to serve requests.
gristServer.setReady(false);
return res.status(200).send({ msg: "ok" });
```

**Flow:** request validated by install-admin gate → if the deployment cannot restart (no supervisor channel), answer 409 WITHOUT touching readiness → else mark the instance not-ready IMMEDIATELY (health checks start failing, load balancers drain) → send 200 → on response FINISH (client got the answer) send `{action:"restart"}` over process IPC so the parent supervising under docker respawns with fresh env.
**Invariant:** ordering is load-bearing: never kill the process before the response finishes, never stay ready after accepting a restart; the restart request rides the SAME response lifecycle so a client timeout can't orphan a half-restarted server. The 409 path must NOT flip readiness.
**Probe:** covered indirectly by admin-page/setup suites (`test/server/lib/SetupRequests.ts`, BootProbes); direct restart-endpoint unit test absent at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "setReady canRestart process.send restart admin", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any app whose configuration lives partly in environment variables: expose an authenticated self-restart that drains via readiness, replies, then asks the supervisor. Adapt the IPC message to your supervisor (docker/s6/k8s). Omit the 409 nuance only if your UI never offers the button conditionally.
