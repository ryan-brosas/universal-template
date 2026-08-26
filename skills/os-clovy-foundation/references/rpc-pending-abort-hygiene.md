<!-- capsule-v2 -->
# RPC pending-request abort hygiene — how do correlated requests survive cancel and teardown?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** How does a duplex NDJSON peer correlate responses to in-flight requests without leaking listeners or hanging promises when the stream dies?

## NdjsonRpcPeer pending map
**Path/Symbol:** `agent-runtime/src/transport.ts:NdjsonRpcPeer.request` (:50-85), `resolveResponse` (:147-154), `close` (:105-113), `listen` (:41-48).
**Signature:** `request(method, params, sessionId, runId, signal?): Promise<JsonValue>`; `close(reason?: Error): void`.
**Data Shape:** `pending: Map<id, {resolve, reject, cleanup?}>` keyed by `crypto.randomUUID()`; responses resolve by echoing that id.

### Decisive source
```ts
const onAbort = () => {
  const pending = this.pending.get(id);
  if (!pending || !this.pending.delete(id)) return;
  pending.cleanup?.();
  pending.reject(abortError());
};
const cleanup = signal ? () => signal.removeEventListener("abort", onAbort) : undefined;
this.pending.set(id, { resolve, reject, ...(cleanup ? { cleanup } : {}) });
signal?.addEventListener("abort", onAbort, { once: true });
this.write(frame);
// listen():
lines.on("close", () => this.close(new Error("Host transport closed")));
// close(): rejects EVERY pending with `reason`, then clears the map.
```

**Flow:** register pending → write frame → response line → `resolveResponse` deletes pending, runs cleanup (removes the abort listener), resolves/rejects (remote `error` frames rethrown as `ProtocolError(code,message,data)`). Abort before settle → delete + cleanup + reject with AbortError. Stream close → `close()` fans the teardown reason to all pending.
**Invariant:** A settled request leaves ZERO abort listeners attached and an empty pending map; a rejected promise is always delivered exactly once (the delete-then-check guard makes late aborts no-ops); unknown response ids are silently dropped rather than crashing.
**Probe:** `agent-runtime/test/transport.test.ts` "removes settled request abort listeners" — FakeAbortSignal counts `added===1 && removed===1` and `peer.pending.size === 0` after settle. Executed live at pin (17/17 suite pass).

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"pending request abort listener cleanup transport", file_pattern:"agent-runtime/*" })
→ src.transport.abortError Function transport.ts 182-186  (rank 1)
   src.transport.NdjsonRpcPeer.request Method transport.ts 50-85
   test.transport.test.FakeAbortSignal Class transport.test.ts 39-61
```

## Verdict
Adopt the id-keyed pending map with cleanup-on-settle and close-fans-rejection — it is the difference between a cancellable peer and a listener leak. Adapt the framing to your wire format; keep the "late abort after settle is a no-op" guard. Omit the specific error strings ("Host transport closed") if your host surfaces its own.
