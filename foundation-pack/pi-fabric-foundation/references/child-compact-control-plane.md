<!-- capsule-v2 -->
# Child compact control plane — how do you compact a child agent's context over RPC and still shut down deterministically?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How does a parent drive a mid-turn compaction inside a child Pi process without racing the child's shutdown?

## Child compact control plane
**Path/Symbol:** `src/agents/compact-control.ts:ChildCompactControl` (queue :56–72, childSettled :74–79, observe :81–109, #startPending :111–136, #maybeFinish/#finish :138–157).
**Signature:** `constructor(runId: string, hooks: {send(frame), close(), update(status), now?})`; `queue(instructions?)`; `childSettled()`; `observe(event)`.
**Data Shape:** Pending `{requestedAt, instructions?}`; InFlight `{id, requestedAt, startedAt, responseSeen, endSeen, error?}`; status publishes `{status: queued|in_flight|completed|failed, requestedAt, updatedAt, attempts, coalescedRequests, ...}`.

### Decisive source
```ts
// #maybeFinish — BOTH events must be observed before close():
#maybeFinish(): void {
    const inFlight = this.#inFlight;
    if (!inFlight || !inFlight.responseSeen || !inFlight.endSeen) return;
    this.#finish(inFlight.error);
}
// id minted per attempt:
const id = `fabric-compact-${this.runId}-${++this.#sequence}`;
```

**Flow:** mid-turn `queue()` only records pending (publish "queued") → `childSettled()` starts it (`agent_settled` is the safe boundary; frame sent with id `fabric-compact-run-1-N`) → `observe()` consumes BOTH the correlated RPC `{type:"response", command:"compact", id}` AND the child's `{type:"compaction_end"}` in EITHER order → both seen → finish → if another request was queued during flight, start it immediately (coalesced follow-on), else `close()` (one-shot shutdown).
**Invariant:** A mid-turn queue NEVER sends before settle; requests arriving during flight coalesce to the LATEST instructions (`this.#pending` overwrite + `this.#coalescedRequests++`, reported in status); RPC rejection (`success !== true`) or `compaction_end` abort/errorMessage fails WITHOUT killing the active turn; shutdown happens exactly once and only after the two-event handshake completes for every queued attempt.
**Probe:** `tests/child-compact-control.test.ts` ("accepts compaction_end before the correlated response" → close NOT called after end alone, called once after late response); grep -c 'runs one coalesced follow-on request before one-shot shutdown' tests/child-compact-control.test.ts → 1.
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ChildCompactControl queue childSettled observe compaction_end", limit: 10 });
// ChildCompactControl.childSettled Method src/agents/compact-control.ts 74-79
```

## Verdict
Adopt the two-event handshake (RPC ack + completion event, order-independent) as the deterministic-shutdown gate for any parent-driven child operation; adapt frame vocabulary to your transport; omit the coalescing counter if your status surface doesn't need observability of dropped duplicates.
