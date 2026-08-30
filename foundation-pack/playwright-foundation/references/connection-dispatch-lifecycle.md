<!-- capsule-v2 -->
# Connection dispatch lifecycle — how does one message pipe serve both promise responses and object events?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When my client sends a command over a single async pipe and receives both replies and unsolicited object events, what ordering/lifecycle rules prevent leaked promises, double-settled callbacks, and hangs after close?

## Message pump with exactly-once callback settlement
**Path/Symbol:** `packages/playwright-core/src/client/connection.ts:Connection.sendMessageToServer` (lines 178-224) + `Connection.dispatch` (234-289).
**Signature:** `sendMessageToServer(object: ChannelOwner, method: string, params: any, options: { apiName?, title?, internal?, frames?, stepId?, signal?, timeout: number }): Promise<any>`; `dispatch(message: object): void`.
**Data Shape:** request `{ id, guid, method, params }` + metadata `{ title, location, internal, stepId, timeout }`; callback map entry `{ resolve, reject, signal, title, type, method }` keyed by numeric id; reply carries `{ id, result | error, errorDetails?, log? }`; events are id-less `{ guid, method, params }`.

### Decisive source
```ts
const id = ++this._lastId;
...
return await new Promise((resolve, reject) => this._callbacks.set(id, { resolve, reject, signal, title: options.title, type, method }));
...
// dispatch():
const callback = this._callbacks.get(id);
if (!callback)
  throw new Error(`Cannot find command to respond: ${id}`);
this._callbacks.delete(id);
```

**Flow:** (1) preflight guards — a closed connection throws its latched `_closedError`, a GC-collected object throws "has been collected", an already-aborted signal throws AbortError immediately; (2) allocate id, emit the outbound message via `this.onmessage` inside `emptyZone.run(...)`; (3) register callback and await; (4) dispatch resolves/rejects by id — **delete-before-settle** guarantees each id settles at most once; (5) id-less messages never touch the callback map: they create objects (`__create__`), reparent (`__adopt__`), dispose (`__dispose__`), or emit a validated event on the GUID's channel.
**Invariant:** A reply whose id has no callback must throw (protocol desync signal), never be silently dropped; after `close()`, every pending callback rejects with the same TargetClosedError instance and the map is cleared so no promise can hang forever.
**Probe:** `grep -c "__create__" packages/playwright-core/src/client/connection.ts` → `1` (single creation path in dispatch); `grep -c "Cannot find command to respond" packages/playwright-core/src/client/connection.ts` → `1`; `grep -c "this._callbacks.delete(id)" packages/playwright-core/src/client/connection.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "sendMessageToServer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-pump dual-role dispatch, delete-before-settle callback discipline, latched-close rejection sweep, and preflight guards for collected objects/aborted signals. Adapt the wire format, metadata fields, and error copy to your transport. Omit Playwright's debugLogger/tracing side-channel (`addStackToTracingNoReply`) unless you port tracing too. Direct tests live in the library suite (`tests/library/browsercontext-events.spec.ts` exercises this pipeline through public API); unit-level coverage of Connection itself is internal-only — verify ports against your own echo-server fixture.
