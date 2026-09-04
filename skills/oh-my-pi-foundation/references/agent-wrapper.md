<!-- capsule-v2 -->
# Agent facade — separate queue ownership from continuation

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Which object owns a prompt, steer, follow-up, and transcript boundary?

## Queue ownership is explicit
**Path/Symbol:** `packages/agent/src/agent.ts:Agent.steer` (994), `followUp` (1003), `peekSteeringQueue` (1040), `continue` (1215–1260s).
**Signature:** `steer(m: AgentMessage)`, `followUp(m: AgentMessage)`, `continue(signal?): Promise<...>`.
**Data Shape:** separate `#steeringQueue`, `#followUpQueue`, active abort controller, durable `#state.messages`.

### Decisive source
```ts
steer(m) {
  this.#steeringQueue.push(m);
  this.#notifySteeringWaiters();
}
followUp(m) { this.#followUpQueue.push(m); }
// non-consuming view used by the in-flight watcher
peekSteeringQueue(): readonly AgentMessage[] { return this.#steeringQueue; }
```

**Flow:** `prompt` owns initial messages → `steer` wakes the active run → tool loop observes (non-consuming, see agent-loop capsule) → boundary drains steering FIRST → follow-up drains only after the current run completes.

**Invariant:** one queue cannot consume the other; the core queues — not a UI mirror — are authoritative.

**Probe:** direct `packages/agent/test/continue-empty-transcript.test.ts:6–55` proves queued steer/follow-up on an empty transcript becomes the opening turn rather than an idle-drain OOM loop.

## Continuation is a state machine, not "run again"
**Path/Symbol:** `Agent.#dequeueSteeringMessagesAfterHooks` (831), `#dequeueFollowUpMessagesAfterHooks` (837), `Agent.continue` (1215+).
**Signature:** boundary dequeue returns `[]` on abort; `continue` selects steering, then follow-up, then valid transcript continuation.
**Data Shape:** an abort-composed dequeue signal and a transcript whose last role controls legal continuation.

### Decisive source
```ts
if (messages.length === 0) {
  const queuedSteering = await this.#dequeueSteeringMessagesAfterHooks(dequeueSignal);
  if (queuedSteering.length > 0) return this.#runLoop(queuedSteering, { skipInitialSteeringPoll: true }, signal, true);
  const queuedFollowUp = await this.#dequeueFollowUpMessagesAfterHooks(dequeueSignal);
  if (queuedFollowUp.length > 0) return this.#runLoop(queuedFollowUp, undefined, signal, true);
  throw new Error("No messages to continue from");
}
```

**Flow:** compose run/deadline signal → hooks → dequeue → start opening turn or resume valid tail → always clear streaming state in `finally`.

**Invariant:** cancellation is run-scoped; empty transcript errors ONLY when both queues are empty; queued steering on an empty transcript skips the initial steering poll (it IS the opening turn).

**Probe:** same direct test covers steer, follow-up, and true-empty failure.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(prompt|continue|steer|followUp|peekSteeringQueue)$", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.agent.src.agent.Agent.continue" });
```

## Verdict
Adopt explicit dual-queue ownership with non-consuming observation and abort-composed boundary dequeues; adapt message types to host transport; omit UI-mirror state entirely. Coverage caveat: tests excluded from graph index by design.
