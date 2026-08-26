<!-- capsule-v2 -->
# Actor stop-the-world halt — how do you interrupt every agent without the interrupt's own completion events re-arming them?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** after a user-level ESC aborts all in-flight agent runs, what stops the resulting `turn_end`/`agent_settled` events from instantly restarting those agents?

## Latched gate lifted only by user input
**Path/Symbol:** `src/actors/manager.ts` → `haltAll` (:914-946), `#beginHostEvent` (:844-867), `#pollMesh` (:1475-1494), getter `halted` (:901-903).
**Signature:** `haltAll(): { halted: number }`; `#beginHostEvent(event, idle): boolean`; `get halted(): boolean`.
**Data Shape:** private `#halted: boolean` latch; host events are a closed set (`input`, `turn_end`, `agent_settled`, `tool_error`, `session_compact`, …); mesh events tail from an offset cursor.

### Decisive source
```ts
// #beginHostEvent — the single gate through which dispatch must pass
if (event === "input" && this.#halted) {
  this.#halted = false;          // resume lifts the latch
  this.#scheduleMeshPoll();      // deferred mesh events flush now
}
if (this.#halted) return false;  // everything else is frozen
```

**Flow:** `haltAll()` aborts each owned actor's `abortController`, rejects every queued item, and sets `#halted=true` **even when nothing is running** (an idle-but-subscribed actor would otherwise be re-armed by the interrupt's own settle events) → while latched, both host-event dispatch (`dispatchHostEvent`) and mesh consumption (`#pollMesh` returns before reading) are suppressed, so deferred events stay preserved → the next user message fires the `"input"` event, which lifts the latch *before* dispatching that same event to input-subscribed actors.
**Invariant:** the gate has NO time-based expiry — only the `"input"` host event lifts it; and it is armed unconditionally (not "only if work was cancelled"). A porter who arms the gate conditionally on `inFlight>0` reintroduces the re-arm race; one who adds a timeout breaks the "deferred until resume" contract.
**Probe:** `tests/actor-manager.test.ts:864` — "haltAll arms a stop-the-world that suppresses host events until the user resumes" (dispatch counts 1→0→0 across event types, then resumes via `input`); :895 pins deferred mesh delivery immediately after resume.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "haltAll stop-the-world halted input", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the unconditional latch + input-only-lift pattern for any multi-agent supervisor with a user interrupt; adapt the lift trigger to whatever your "user spoke again" signal is; omit the mesh-cursor deferral detail if you have no event log. Direct tests pin both suppression and resume — no coverage caveat.
