<!-- capsule-v2 -->
# dispatch-command-router — in what order must a hub command router apply authority, drain, and capability gates, and how does it answer when a subsystem is missing?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should a single WS/IPC envelope router separate trust resolution from routing, refuse work during drain, and degrade typed-but-unavailable subsystems without throwing?

## Authority before dispatch; drain refusal set; degraded-capability reply duality
**Path/Symbol:** `sdk/packages/core/src/hub/server/hub-server-transport.ts` (`handleCommand` :670-705, `dispatchCommand` :707-867, `captureFailedReply` :869-891); drain set `hub/server/handlers/run-queue-handlers.ts:26-54` (`HUB_DRAINING_ERROR_CODE`, `DRAIN_REFUSED_COMMANDS`, `isDrainRefusedCommand`, `drainingReply`).
**Signature:** `handleCommand(envelope, authority?: HubConnectionAuthority | null) → Promise<HubReplyEnvelope>`; `dispatchCommand(envelope, authority?)` is private; `drainingReply(envelope)` → `{ok:false, error:{code:"hub_draining", details:{retryable:true}}}`.
**Data Shape:** HubCommandEnvelope{version, requestId, command, clientId?, sessionId?, payload?}; replies always echo version+requestId. Graph evidence: dispatchCommand has exactly one caller (handleCommand).

### Decisive source
```ts
// handleCommand — authority is resolved BEFORE any routing, from transport trust:
//   Omitted authority is reserved for trusted in-process callers. A remote
//   transport passes null until registration so caller-controlled envelope
//   fields can never acquire daemon workspace authority implicitly.
const effectiveAuthority =
	authority === undefined
		? this.options.workspaceRoot?.trim() && clientId ? {clientId, workspaceContext:{...}} : undefined
		: (authority ?? undefined);          // null stays null => no implicit authority

// dispatchCommand — gate order matters:
if (this.draining && isDrainRefusedCommand(envelope.command)) return drainingReply(envelope);
if (isAgendaTaskCommand(envelope.command)) return await this.taskCommands.handleCommand(envelope, authority);
switch (envelope.command) { /* client.*, session.*, run.*, hub.drain/status, capability.*, ui.*, connector.* -> handleConnectorCommand */ 
  case "run.enqueue": { if (!this.runQueue || !this.runExecutor) return { ...ok:false, error:{code:"run_queue_unavailable", message:"This hub has no durable run queue; use run.start instead."} }; }
  case "run.list":    { if (!this.runQueue) return okReply(envelope, { runs: [] }); }   // degraded = OK-empty, not error
  case "settings.get": case "settings.patch": return { ...ok:false, error:{code:"not_implemented", message:`${envelope.command} is not implemented yet.`} };
  default: /* schedule delegation; publish hub event only when reply.ok && eventNameForScheduleCommand maps */ }
```

**Flow:** resolve authority (undefined=in-process trusted w/ clientId+workspaceRoot, null=remote pre-registration ⇒ none) → drain gate refuses ONLY work-admitting commands (session.create/restore/fork, run.start, session.send_input, run.enqueue) with a retryable typed reply → agenda delegation → command switch → default schedule delegation with conditional event publication → outer catch captures SDK telemetry and rethrows; failed replies are captured only for allowlisted error codes (session_not_found downgrades to warn).
**Invariant:** Authority never derives from envelope content — only from transport-established trust. Drain refusal must be total for anything that admits new work but never blocks introspection/status. Missing capability has two honest shapes: ERROR with actionable code when the operation cannot be served (run.enqueue), OK-empty when the empty result is the truth (run.list); unimplemented ≠ unavailable (`not_implemented`). Every reply echoes version+requestId so late/mismatched correlation stays impossible.
**Probe:** `grep -cF 'if (this.draining && isDrainRefusedCommand(envelope.command)) {' …hub-server-transport.ts` → 1; `grep -cF 'export const HUB_DRAINING_ERROR_CODE = "hub_draining";' …run-queue-handlers.ts` → 1; `grep -cF 'code: "run_queue_unavailable",' …hub-server-transport.ts` → 1; `grep -nF 'authority === undefined' …` → line 680. Direct tests: handlers/connector-handlers.test.ts ("starts a connector through the supervisor", "passes the restart intent through", "reports clearly when the hub has no supervisor"), singleton.e2e.test.ts real-process lock cases. All executed pre-write, exit 0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "cline", function_name: "dispatchCommand", direction: "inbound", depth: 1 });
// observed: callers_total 1 — only HubServerTransport.handleCommand routes into dispatchCommand
```

## Verdict
Adopt the three-layer ordering (trust resolution → refusal gates → routing table), the explicit undefined-vs-null authority contract, the drain-refused allowlist of work-admitting commands, and the two-shape degraded-capability discipline. Adapt command vocabulary and event-publication mapping to host domains. Omit Cline's specific session/schedule handler families. Complements ws-command-envelope (client side): that capsule owns requestId correlation; this owns server-side admission. Runner-BLOCKED here; probes green.
