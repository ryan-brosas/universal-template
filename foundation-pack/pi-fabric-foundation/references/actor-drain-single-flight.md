<!-- capsule-v2 -->
# Actor drain single-flight — how do you run one agent's message queue with exactly one loop and never strand an item?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** when a host event can enqueue work from any callback while a run is in flight, what invariant keeps exactly one consumer loop alive per actor?

## Single-flight drain with synchronous release
**Path/Symbol:** `src/actors/manager.ts` → `#ensureDrain` (:1084-1100), `#drain` (:1102-1262), `#enqueue` (:1002-1074).
**Signature:** `#ensureDrain(actor): void`; `async #drain(actor): Promise<void>`; `#enqueue(actor, source, payload, options?): ActorQueueItem`.
**Data Shape:** `ManagedActor` carries `queue: ActorQueueItem[]`, `draining: boolean`, `drain?: Promise<void>`, `status: "idle"|"queued"|"running"|"stopped"`. Queue items carry optional `coalesceKey`, `resolve/reject` (for blocking `ask()`), and a monotonically increasing `activation.sequence`.

### Decisive source
```ts
#ensureDrain(actor: ManagedActor): void {
  if (actor.draining || actor.status === "stopped" /* ... */) return;
  actor.draining = true;
  const drain = this.#drain(actor);
  actor.drain = drain;
  const release = (): void => {
    if (actor.drain === drain) delete actor.drain;
  };
  drain.then(release, release);
}
// ...inside #drain's outer finally:
actor.draining = false;
```

**Flow:** enqueue pushes the item, sets `status="queued"` → `#ensureDrain` flips `draining=true` synchronously before awaiting anything → the `while` loop shifts one item, runs it (`agents.run`), settles it → loop re-checks queue length → on exit the **outer** `finally` clears `draining=false` *before* the promise settles → any enqueue landing in that microtask window sees `draining===false` and starts a fresh drain.
**Invariant:** the flag is cleared in a synchronous `finally` at loop exit, NOT in a `.then()` after settlement; identity-checking `actor.drain === drain` makes a stale release harmless. A porter who resets `draining` inside `.then(release)` after `await` boundaries reintroduces the "stuck at queue:1" race the comment names explicitly.
**Probe:** `tests/actor-manager.test.ts:1050` — "restarts the drain for successive coalesced host events without stranding an item": five sequential idle-then-event turns each dispatch 1 delivery; a regression leaves `queued:1` stranded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "#ensureDrain draining single flight", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synchronous-flag single-flight drain pattern for any per-entity FIFO queue fed by reentrant callbacks; adapt the coalesce-key replacement (`existing.payload = structuredClone(payload)` refreshes the queued item in place) to your message shape; omit the mesh-presence publishing interleaved between runs. Direct tests exist and pin the race — no coverage caveat.
