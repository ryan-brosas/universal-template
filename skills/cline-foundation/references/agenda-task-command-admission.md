<!-- capsule-v2 -->
# Agenda task-command admission — how does a hub command layer derive task identity and authority without ever trusting the payload?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** when remote clients send `task.*` commands over a hub socket, what stops a spoofed actor, a forged workspace, or a cross-workspace read?

## Authority-derived admission in `HubAgendaTaskCommandService`
**Path/Symbol:** `sdk/packages/core/src/hub/server/task-command-service.ts:56-179` (`handleCommand`), helpers `resolveWorkspace` :181-187, `requireScopedTask` :189-202, `requiredRevision` :41-51; delegation point `hub-server-transport.ts:714-716`.
**Signature:** `handleCommand(envelope: HubCommandEnvelope, authority?: HubConnectionAuthority): Promise<HubReplyEnvelope>` — every command resolves the workspace from the *connection* authority first.
**Data Shape:** envelope carries `{version, command, requestId, clientId?, payload}`; authority carries `{clientId, workspaceContext:{workspaceRoot, cwd}}`; replies are `okReply`/`errorReply` echoing version+requestId.

### Decisive source
```ts
const workspaceRoot = this.resolveWorkspace(authority);   // throws before any switch arm runs
// ...
case "task.create": {
    const task = await this.tasks.createTask({
        ...(payload as unknown as AgendaTaskCreateInput),
        scope: "workspace",          // forced — payload cannot nominate global
        workspaceRoot,               // forced to the AUTHORITY root
        cwd: workspaceRoot,
        requiresApproval: false,
        createdBy: actor,            // synthesized from envelope.clientId AFTER spread:
    });                              // a spoofed payload createdBy is overwritten
```
```ts
private resolveWorkspace(authority?: HubConnectionAuthority): string {
    const workspaceRoot = authority?.workspaceContext?.workspaceRoot?.trim();
    if (!authority?.clientId || !workspaceRoot) {
        throw new Error("task commands require a Hub-authorized workspace");
    }
    return resolve(workspaceRoot);
}
private async requireScopedTask(payload, workspaceRoot) {
    const task = await this.tasks.getTask(taskIdOf(payload));
    if (!task ||
        (task.scope === "workspace" &&
         (!task.workspaceRoot || resolve(task.workspaceRoot) !== workspaceRoot))) {
        throw new Error("task does not exist in this workspace");   // existence-hiding
    }
    return task;
}
```

**Flow:** transport drain gate → `isAgendaTaskCommand` delegates BEFORE the main switch (:714-716) → `resolveWorkspace` (unregistered/remote callers get nothing, not even `task.list`) → per-command: create forces scope/root/cwd/actor; get/update/approve/cancel/run pass through `requireScopedTask`; approve/cancel/run additionally call `requiredRevision` (positive-integer gate at the ENVELOPE layer, while update/get defer concurrency to the store CAS); `task.automation.set` overwrites any payload `scopeKey` with the resolved root (:159-162). Every throw lands in one catch producing `task_command_failed`.
**Invariant:** identity and scope come only from the connection authority; payload fields can never self-authorize. Cross-workspace access fails with an existence-hiding message identical to a missing id. `task.list` deliberately MERGES workspace + global scopes in one reply (:80-97) — global work is visible to every registered client, other workspaces are invisible.
**Probe:** `task-command-service.test.ts` (274L, 7 cases): "uses the authenticated Hub client as the create actor" pins the spoofed `createdBy:{kind:"system"}` being discarded (`toHaveBeenCalledWith(expect.objectContaining({createdBy:{kind:"user",id:"desktop",clientId:"desktop"}}))`, :106-115); it.each over approve/cancel/run pins `"expectedRevision must be a positive integer"` for a missing revision (:223-242).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "agenda hub task command service workspace authority admission", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "cline", function_name: "cline.sdk.packages.core.src.hub.server.task-command-service.HubAgendaTaskCommandService.handleCommand", direction: "inbound", depth: 2 });
```
(Verified this pass: callers_total=2 — `dispatchCommand` and `handleCommand` re-entry.)

## Verdict
Adopt authority-derived identity with post-spread forced fields (payload spread first, trusted fields after) and existence-hiding scoped lookups. Adapt the authority shape to your transport; keep revision gates on mutating commands if your store uses optimistic concurrency. Omit the hub envelope machinery if your caller is in-process. Runner caveat: upstream vitest not executable here (no node_modules) — evidence is whole-file direct reads + live graph retrieval.
