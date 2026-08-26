<!-- capsule-v2 -->
# Send-chain serialization — how do you keep ordered protocol messages flowing through one async transport without interleaving or losing failures?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** Multiple event handlers want to `await transport.send(...)` — how do you serialize them, preserve order, survive a stopped session, and never let one rejected send break the queue?

## Send chain
**Path/Symbol:** `src/live/controller.ts:#queueSend` (:459-467); field `#sendChain: Promise<void> = Promise.resolve()` (:128); drain consumer `#stop` :286.
**Signature:** private `(message: LiveClientMessage): void` — fire-and-forget enqueue; ordering guaranteed, no per-call promise exposed.
**Data Shape:** A self-replacing promise chain; each link checks `#stopped` again at execution time (not just enqueue time).

### Decisive source
```ts
#queueSend(message: LiveClientMessage): void {
  const transport = this.#transport;
  if (!transport || this.#stopped) return;      // enqueue-time gate
  this.#sendChain = this.#sendChain
    .then(async () => {
      if (!this.#stopped) await transport.send(message);   // run-time re-gate
    })
    .catch((cause) => this.#reportFailure(errorFrom(cause))); // chain NEVER rejects
}
```

**Flow:** every outbound delegation-context chunk (`#handleDelegation`, `handleAgentMessage`, `handleAgentSettled`) funnels here → appended to the chain tail → executed strictly in enqueue order once prior sends settle → a failed send converts to `#reportFailure` so the chain itself always resolves, keeping later messages meaningful to attempt or moot via stop. Because `#stop()` awaits `this.#sendChain` BEFORE sending `session.close` (:286-291), everything already queued drains in order ahead of the close frame.
**Invariant:** Message order equals call order (single chain, no concurrency); the chain never enters a rejected state — one failed send must not poison successors; double-gating (enqueue-time + run-time) makes a stop racing an enqueue safe: at worst the message is skipped, never sent after close. Callers get no backpressure signal by design — delegation context is best-effort with failure surfaced through the terminal latch instead.
**Probe:** `tests/live-controller.test.ts` (:29-31 `flushSends` helper spins microtasks so chained sends resolve before assertions; :96-114 asserts BOTH commentary and final context appends arrive with correct payloads after settlement; :133 proves the drained chain precedes `session.close`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "queueSend sendChain transport.send", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the self-healing promise-chain serializer with enqueue/run-time double stop-gates for ordered best-effort sends. Adapt failure routing if you need per-message acks (this design deliberately has none). Omit the specific message builders (protocol layer). Caveat: no upstream test pins out-of-order rejection recovery directly — ordering evidence is indirect via flushSends payload assertions.
