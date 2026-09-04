<!-- capsule-v2 -->
# Bridge pending-call lifecycle — what must a pending-call map guarantee when the caller aborts, the socket dies, or the write backpressures?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** What must a pending-call map guarantee when the caller aborts, the socket dies, or the write backpressures — so no request is ever left unsettled?

## Pending-call lifecycle
**Path/Symbol:** `src/pi-extension/acp-mcp-bridge.ts` — `callRemoteTool` :648-704, `send` :513-520, `connect` close handler :638-646, `handleMessage` result/error branches :605-612.
**Signature:** `function callRemoteTool(tool: BridgeTool, args: Record<string, unknown>, requestId: string, signal?: AbortSignal): Promise<PiMcpToolResult>`; `function send(msg: IpcMessage): void`.
**Data Shape:** `pending: Map<string, { resolve, reject }>` keyed by the adapter-supplied requestId (composite ids like `<toolCallId>:mutate`, `<toolCallId>:open:<i>` from executeMutationComposite); abort sends `{ type: 'cancel', id }` over IPC.

### Decisive source
```ts
// pre-aborted: reject BEFORE registering anything
if (signal?.aborted) { pending.delete(requestId); failed(new Error('IDE tool call cancelled')); return }
// abort mid-flight: remove the entry FIRST (so a late result cannot resolve a dead call),
// tell the remote to stop, then settle locally
const onAbort = () => {
  if (!pending.delete(requestId)) return        // already settled — do not double-cancel
  send({ type: 'cancel', id: requestId })
  failed(new Error('IDE tool call cancelled'))
}
// write failure / destroyed socket: synchronous cleanup, no orphan entry
let ok = true
try {
  if (!sock || sock.destroyed) ok = false
  else sock.write(JSON.stringify({ type: 'call', id: requestId, tool: tool.exposedName, args }) + '\n')
} catch { ok = false }
if (!ok) { pending.delete(requestId); signal?.removeEventListener('abort', onAbort); failed(...) }
// disconnect: fan-out rejection of every pending call, then clear
sock.on('close', () => {
  sock = undefined; registered = false
  const error = new Error('IDE bridge IPC disconnected; IDE tools unavailable')
  for (const [, call] of pending) call.reject(error)
  pending.clear()
  ...
})
```

**Flow:** `callRemoteTool` guards `!sock || sock.destroyed || !registered` up front (rejects without touching the map). The happy path registers `{resolve: done, reject: failed}` — `done` runs the result through `mcpResultToPiResult` + IDE-mode result filtering before resolving, so mapping errors reject the SAME promise. Abort handling: a pre-aborted signal rejects before registration; a mid-flight abort deletes the entry (the `pending.delete` return value is the idempotence guard — a settled call never sends a spurious cancel), emits the IPC `cancel` frame, and settles. `send` is fire-and-forget: it try/catches the socket write and treats `write() === false` as backpressure, NOT failure (the reply still arrives; test-pinned). Disconnect closes the socket and rejects every pending entry with one shared error, then clears the map; `handleMessage` result/error branches delete-then-settle so a duplicate frame for a settled id is a no-op.
**Invariant:** every pending entry settles exactly once, by exactly one of: result frame, error frame, abort, disconnect fan-out, or write failure — and the entry is removed from the map BEFORE its settlement side effects (cancel frame, fan-out) run, so no path can observe a settled entry as pending. Abort listeners are removed on every settle path to avoid leaks.
**Probe:** `test/unit/acp-mcp-extension.test.ts` — 'cancellation during a pending call cleans pending state' (:748), 'new IDE calls after disconnect fail immediately without pending entries' (:543), 'repeated disconnect is idempotent' (:552), 'write returning false is backpressure, not failure' (:813, read this pass: fake socket returns `false` from write, call still resolves with the reply, exactly one call emitted). Executed GREEN at this pin (pass-7 fleet).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "callRemoteTool pending cancel abort disconnect backpressure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the settle-exactly-once pending map: delete-before-side-effect ordering, the `pending.delete` return value as double-settle guard, pre-aborted fast reject, disconnect fan-out with a shared error, and backpressure-tolerant fire-and-forget sends. Adapt the cancel-frame vocabulary to your IPC protocol. Omit the composite-requestId convention if your calls never fan out per mutation. Direct tests exist and were executed green at the pin.
