<!-- capsule-v2 -->
# Execution-service host-call switch — one dispatch point where budgets, deadlines, discovery, and handoffs wrap every sandbox→host call

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** when guest code in a sandbox calls back into the host, where do you enforce agent budgets, full-code walls, deadline floors, and trace attribution without scattering checks across providers?

## Connected graph-selected seam
**Path/Symbol:** `src/execution-service.ts` — `FabricExecutionService.execute` (:151-707): `loadRuntimeDependencies` lazy import (:54-65), `aggregateUsage` (:82-101), `maxAgentCalls` clamp (:203-209), `guardAgentCall` (:210-221), `fullCodeProvider` (:222-226), `guardFullCodeRef` (:227-234), coalescing emit (:235-274), `minimumTimeoutMsForHostCall` (:307-347), `traceAttempt` (:348-366), `invokeAction` (:367-422), host-call switch (:432-669), `finally { endInvocation; flushEmit }` (:685-688).
**Signature:** `execute(options)` → `FabricExecutionResult {success, value, logs, audits, phases, trace, elapsedMs, typeErrors?, error?, handoffRequest?, usage?}`; the runtime receives ONE async `(ref, args, runtimeSignal)` callback that switches on the full internal-ref surface.
**Data Shape:** guard refs set = `{agents.run, agents.handoff, agents.spawn, agents.create}` (budgeted); blocking orchestration refs = `{agents.run, agents.wait, agents.ask}` (deadline-raising, see orchestration capsule).

### Decisive source
```ts
const maxAgentCalls = Math.max(
  1,
  Math.min(
    options.maxAgentCalls ?? this.config.agents.maxPerExecution,
    this.config.agents.maxPerExecution,
  ),
);
const guardAgentCall = (ref: string): void => {
  if (
    ref !== "agents.run" &&
    ref !== "agents.handoff" &&
    ref !== "agents.spawn" &&
    ref !== "agents.create"
  ) return;
  agentCalls++;
  if (agentCalls > maxAgentCalls) {
    throw new Error(`Fabric agent budget exhausted (${maxAgentCalls} per execution)`);
  }
};
```

**Flow:** type-check FIRST (errors ⇒ return with `trace.seal("failed", …)` and NO audits — code never ran). Per execution: one ApprovalController sharing session approvals + classifier usage collector. Every nested call flows through either `invokeAction` (guards → registry.invoke with injected `deferHandoff` for agents.handoff ONLY — second handoff throws `"Only one agents.handoff request is allowed per fabric_exec invocation"` and returns `{scheduled:true, status:"deferred", boundary:"fabric_exec_end"}`, authorizer hook, approve with schema.commit promoted to write+execute double approval, shared audits array, observeInvocation) or `traceAttempt` (discovery/workflow refs: `$providers`, `$catalog`, `$models`, `$list`, `$search`, `$describe`, `$progress`, `$configure`, `$phase`, `$item`, `$event`, `$spanStart/End`) — both attribute failures to a failureStage (`invoke|guard|resolve|validate|approve`). Discovery results filter out pi./extensions. providers when NOT effectiveFullCodeMode via `fullCodeProvider` = split at the FIRST `.` (`value.indexOf(".")`, never split/lastIndexOf — provider names cannot contain dots but tool ids after it may contain anything). Deadline floor logic: orchestration programs start at `max(executor.timeoutMs, agents.timeoutMs)`; each host call re-raises via `minimumTimeoutMsForHostCall` — pi.bash adds requested timeout +5s grace capped at MAX_AGENT_TIMEOUT_MS; blocking orchestration refs raise to `max(orchestrationTimeoutMs, requested agents.run timeoutMs clamped [MIN_AGENT_TIMEOUT_MS, MAX])`; computed refs arrive as `fabric.$call {ref,args}` and are UNWRAPPED before classification so aliased agent calls get the same floor. Progress emission is one execution-wide leading-edge-throttled timer (`if (emitTimer) return` — deliberately NOT trailing debounce, which starves streaming tools), flushed on settle; nested metadata call gets synthetic id `<parentToolCallId>_metadata`. Runtime instance is cached per executor kind (`#runtimeKind !== runtimeKind` rebuilds). Classifier usage aggregates into result.usage only when non-empty.
**Invariant:** (1) Budget counts CALLS not successes — a rejected spawn consumes budget; the cap is caller-request CLAMPED by config ceiling (a caller can lower but never raise). (2) The full-code wall lives at THIS layer, not per-provider: even a hostile computed ref through tools.call hits `guardFullCodeRef` before resolve, so orchestration-only mode cannot reach pi.* even indirectly (`tests :449` pins empty catalog + thrown errors + EMPTY audits). (3) Handoff deferral is injected ONLY into the agents.handoff invocation context and is single-shot per execution; the deferred request rides OUT on the result, and the actual fork happens later at the outer message boundary (prewalk capsules). (4) schema.commit approval is silently upgraded to write+execute — a commit must pass BOTH risk gates even though its descriptor says one. (5) `finally` always runs `registry.endInvocation(parentToolCallId)` then `flushEmit()` — late callbacks no-op because invocationActive flipped (see action-registry-invoke-stages capsule). (6) fabric.$models swallows registry errors to `[]` while still tracing the failure — model discovery must never kill an execution.
**Probe:** `tests/execution-service.test.ts:574` ("enforces the per-execution agent budget" — 2 parallel runs vs max 1 ⇒ error contains `agent budget exhausted (1 per execution)`), `:627` ("raises the executor deadline to the agent deadline for orchestration programs"), `:677` ("extends the outer deadline from an explicit pi.bash timeout"), `:721` ("raises the deadline for literal and computed generic agent refs"), `:783` ("audits auto approvals and accounts for classifier usage"), `:858` ("keeps the short executor deadline for non-orchestration programs"), `:14` ("defers explicit handoff and completes every later call in the same program"), `:242` ("coalesces all parallel nested calls through one global debounce and flushes on settle"), `:357` ("throttles continuous nested progress without starving intermediate snapshots"), `:310` ("ignores late nested updates after activity resets during execution"), `:449` ("keeps Pi core tools outside Fabric in orchestration-only mode").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "FabricExecutionService execute guardAgentCall guardFullCodeRef minimumTimeoutMsForHostCall invokeAction traceAttempt deferHandoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-switch host-call dispatch with layered guards (budget → full-code wall → deadline floor → trace stage) and the clamp-don't-raise budget contract; adapt ref names and the internal `$verb` surface. The portable lesson: put cross-cutting execution policy at the ONE place every callback passes through, and make computed references unwrap before classification.
