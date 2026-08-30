<!-- capsule-v2 -->
# Schedule command scope isolation — how does a per-workspace schedule service confine every read and write to the caller's registered workspace?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** when clients register with a workspaceRoot, how do you stop one workspace's client from listing, triggering, or re-cwding another workspace's schedules?

## Registered-workspace scoping in `HubScheduleCommandService`
**Path/Symbol:** `sdk/packages/core/src/cron/service/schedule-command-service.ts` (301 lines whole): `resolveScope` :178-193, `requireScopedSchedule` :195-207, `scopedCwd` :17-27 + `pathWithin` :29-32, `toCreateInput` :244-267, `toUpdateInput` :269-300; default-branch entry `hub-server-transport.ts:853-865`.
**Signature:** `handleCommand(envelope, authority?)` — unlike task commands, there is NO per-arm guard: `resolveScope` throws once at the top, so EVERY schedule verb (even `schedule.list`) requires a registered workspace.
**Data Shape:** scope = `{workspaceRoot: resolve(root), cwd: resolve(cwd||root)}`; every input is rebuilt as `{...payload, modelSelection, mode?, workspaceRoot: scope.workspaceRoot, cwd?}`.

### Decisive source
```ts
private resolveScope(authority?: HubConnectionAuthority): ScheduleCommandScope {
    const context = authority?.workspaceContext;
    if (!authority?.clientId || !context?.workspaceRoot?.trim())
        throw new Error("schedule commands require a registered workspace client");
    const workspaceRoot = resolve(context.workspaceRoot);
    const cwd = resolve(context.cwd?.trim() || workspaceRoot);
    if (!pathWithin(workspaceRoot, cwd))
        throw new Error("client cwd is outside its workspace scope");
    return { workspaceRoot, cwd };
}
private requireScopedSchedule(envelope, scope) {
    const scheduleId = String(envelope.payload?.scheduleId ?? "").trim();
    const schedule = scheduleId ? this.schedules.getSchedule(scheduleId) : undefined;
    if (!schedule || resolve(schedule.workspaceRoot) !== scope.workspaceRoot)
        throw new Error("schedule does not exist in this workspace");   // existence-hiding
}
function scopedCwd(scope, value) {
    if (typeof value !== "string" || !value.trim()) return undefined;
    const cwd = resolve(scope.workspaceRoot, value);
    if (!pathWithin(scope.workspaceRoot, cwd))
        throw new Error("schedule cwd is outside the client workspace scope");
    return cwd;
}
```

**Flow:** create defaults `mode` via `readHubScheduleMode(payload, "yolo")` (absent key ⇒ "yolo"; present-but-invalid ⇒ throw; shared/src/hub.ts :392-404) and accepts either a `modelSelection` object or a legacy `provider/model` pair → update includes `cwd` ONLY when `Object.hasOwn(payload,"cwd")`, treating explicit `null` as reset-to-root (`payload.cwd === null ? scope.workspaceRoot : scopedCwd(...) ?? scope.cwd`) — presence-keyed, not truthiness-keyed, so `cwd:""` cannot sneak past as "no change" while `null` still means reset → list/active/upcoming/executions filter results through `scopedScheduleIds` (a Set built from the caller's root) instead of trusting payload filters.
**Invariant:** unregistered callers fail before any arm runs; cross-root ids are indistinguishable from missing ones; payload can never widen its own scope — even `workspaceRoot` in the payload is overwritten by `scope.workspaceRoot` after spread.
**Probe:** `agenda-task-hub.test.ts` :247-294 pins exactly this on the vertical slice: `transport.handleCommand({command:"schedule.list", clientId:"unregistered-client"}, null)` rejects with code `schedule_command_failed`, message "schedule commands require a registered workspace client", then a `client.register`ed client lists its own workspace's schedules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "schedule command service scoped workspace resolveScope requireScopedSchedule", limit: 12 });
```
(Verified this pass: ranks `requireScopedSchedule` #1 (-50.24) and `resolveScope` #2.)

## Verdict
Adopt top-of-handler single-scope resolution plus post-spread forced fields for any multi-tenant command surface. Adopt presence-keyed optional updates (`Object.hasOwn`) when null means reset. Adapt the containment predicate to your path library but keep the relative()-prefix form. Omit the legacy provider/model twin if you have no wire-compat burden. Runner caveat recorded honestly (no node_modules).
