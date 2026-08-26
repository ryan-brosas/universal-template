<!-- capsule-v2 -->
# Call-time capability rejection — where should a supervisor reject operations a runner can't support: at the call, or silently after the command is queued?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you guarantee a caller learns about an unsupported operation at call time instead of losing the command inside a child that has no channel to receive it?

## Reject before any side effect; leave mode setters ungated
**Path/Symbol:** `src/agents/manager.ts` — recursion gate :485-489 (`AgentManager.spawn`, starts :463), steer gate `#requireSteerable` :878-884 called from `steer` :865-868 and `followUp` :870-873; deliberately UNGATED siblings `setSteeringMode`/`setFollowUpMode` (:886-892) and `compact` (Pi-only rejection :900-906); queue writer `#appendSteer` :913-930.
**Signature:** `#requireSteerable(id: string): void`; `steer(id, message, data?): AgentSteerResult`; `followUp(id, message, data?): AgentSteerResult`.
**Data Shape:** throws carry the capability vocabulary verbatim — `"Veda runner does not support recursive Fabric. Use a Pi runner for recursive: true — Veda executes one headless prompt per invocation."` (:485-489) and `"The Veda runner does not support steering or follow-ups: Veda executes one headless prompt per invocation. Start a new run instead."` (:878-884). Success shape is `{queued: true, messageId}` from the steer channel append.

### Decisive source
```ts
// src/agents/manager.ts:874-884 — the whole pattern in 11 lines
// Veda children run one headless prompt per invocation; there is no stdin
// turn channel to steer into. Reject steer/follow-up here so callers learn
// at call time instead of the command being silently dropped by the worker.
#requireSteerable(id: string): void {
  if (this.#requireRun(id).runner === "veda") {
    throw new Error(
      "The Veda runner does not support steering or follow-ups: Veda executes one headless prompt per invocation. Start a new run instead.",
    );
  }
}
```

**Flow:** `steer()`/`followUp()` first resolve the run (`#requireRun`) and throw for veda-runner children → ONLY then does `#appendSteer` read `status.json`, reject already-terminal runs ("steering has no target"), and append `{...entry, id: uuid, ts}` to `steer.jsonl`. Because the guard runs before any write, a rejected call leaves zero residue: no run directory, no channel line, no partial state.
**Invariant:** the failure mode being prevented is SILENT DROP — pre-drift, a steer aimed at a headless child was appended to a channel nothing ever read (docs/agents.md said "a steer/follow-up is dropped"; upstream 06a13dd changed the contract to throw-at-call-time). Mode setters stay ungated because they are advisory state on the manager, not commands a child must consume. The error message doubles as remediation advice: "Start a new run instead."
**Probe:** `tests/worker-e2e.test.ts:222` ("rejects steering and follow-ups for Veda children at call time": spawn a real fake-veda child, `expect(() => manager.steer(handle.id, "redirect")).toThrow(/does not support steering/)`, same for `followUp`); recursion twin at :208 ("rejects recursive Fabric for the Veda runner", `/does not support recursive Fabric/`). Claude's recursion twin: :480-484.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "requireSteerable steering follow-ups Veda runner", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt call-time throwing with remediation-bearing messages for any parent→child operation whose receiving channel doesn't exist in some child kind; place the check before every side effect and keep pure-mode setters outside the gate. Adapt the capability vocabulary (recursive/steer/followUp/compact) to your runner matrix; omit per-message error text as API surface. Direct e2e coverage exists but is skipped without a built worker (`describe.skipIf(!hasWorker)`); the deterministic probe anchors above stand in.
