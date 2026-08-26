<!-- capsule-v2 -->
# Pi-tools rendezvous board — how do I let a foreign agent's in-flight tool call wait for a host that only responds on its NEXT request, without losing either side's early arrival?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** When the remote agent emits a tool call over its event stream but the host can only deliver results on a later request, what data structure makes the two sides meet regardless of which arrives first?

## Four-map board tolerates both race orderings
**Path/Symbol:** `src/pi-tools-bridge.ts:PiToolsBridgeBoard` (54-178).
**Signature:** `class PiToolsBridgeBoard { noteToolCall(id: string, droidToolName: string): void; waitForPiResult(toolName: string): Promise<BridgedToolResult>; deliverResults(results: BridgedToolResult[]): void; rejectAll(message: string): void }`
**Data Shape:** `pendingHandlers: Map<toolCallId, {toolName, resolve}>` — handlers suspended inside MCP; `earlyResults: Map<toolCallId, BridgedToolResult>` — results delivered before a handler attached; `waitingByName: Map<sanitizedName, Array<(id)=>void>>` — handlers that started before any id was seen; `unusedIdsByName: Map<sanitizedName, string[]>` — ids seen before any handler waited.

### Decisive source
```ts
noteToolCall(id, droidToolName) {
  // ...
  const waiters = this.waitingByName.get(sanitized);
  if (waiters && waiters.length) {
    const wake = waiters.shift()!;
    if (!waiters.length) this.waitingByName.delete(sanitized);
    wake(id);                       // handler was first → hand it the id
    return;
  }
  const queue = this.unusedIdsByName.get(sanitized) ?? [];
  queue.push(id);                   // id was first → park it for the handler
  this.unusedIdsByName.set(sanitized, queue);
}

waitForPiResult(toolName): Promise<BridgedToolResult> {
  // ...
  const existing = takeId();        // an id already parked? attach immediately
  if (existing) return attach(existing);
  // Handler beat the stream event — wait for noteToolCall to supply the id.
  return new Promise((resolve) => {
    const list = this.waitingByName.get(sanitized) ?? [];
    list.push((id) => { void attach(id).then(resolve); });
    this.waitingByName.set(sanitized, list);
  });
}

deliverResults(results) {
  for (const result of results) {
    const pending = this.pendingHandlers.get(result.toolCallId);
    if (pending) { this.pendingHandlers.delete(...); pending.resolve(result); }
    else this.earlyResults.set(result.toolCallId, result);   // result beat the handler
  }
}
```

Teardown resolves instead of rejecting, and wakes name-waiters with synthetic ids:
```ts
rejectAll(message: string): void {
  for (const [id, pending] of this.pendingHandlers)
    pending.resolve({ content: [{ type: "text", text: message }], isError: true, toolCallId: id });
  this.pendingHandlers.clear();
  this.earlyResults.clear();
  for (const waiters of this.waitingByName.values())
    for (const wake of waiters) wake(`orphaned-${Date.now()}`);
  this.waitingByName.clear();
  this.unusedIdsByName.clear();
}
```

**Flow:** stream `ToolCall` → `noteToolCall` (wake a parked waiter OR buffer id) → MCP handler `waitForPiResult` (attach to buffered id OR park itself) → host's next request calls `deliverPiToolResults` → `deliverResults` resolves the pending promise or stashes in `earlyResults`. Teardown path: `rejectAll` resolves every pending handler with an isError text result, clears stashed state, wakes name-waiters with `orphaned-<ts>` ids.
**Invariant:** Neither side may lose its early arrival: ids-before-handler land in `unusedIdsByName`, handlers-before-id park in `waitingByName`, results-before-handler land in `earlyResults`. Rejection is never thrown at the remote agent — teardown RESOLVES with `isError` text so the foreign loop treats it as ordinary failed tool output.
**Probe:** `test/pi-tools-bridge.test.ts:29-54` pins both orderings ("matches handler that starts before stream noteToolCall" / "matches stream noteToolCall before handler") end-to-end through waitForPiResult → noteToolCall → deliverResults.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "PiToolsBridgeBoard noteToolCall waitForPiResult deliverResults rejectAll earlyResults", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the four-map shape (pending-by-id, early-results-by-id, waiters-by-name, buffered-ids-by-name) and resolve-with-isError teardown for any host↔agent tool bridge where results arrive on a different request than the call. Adapt map keys to your id/name scheme. Omit the Droid-specific sanitized-name keying if your transport already hands you stable ids. Direct test covers both race orders; the rejectAll wake-with-synthetic-id path is source-read-only (no dedicated test — caveat).
