<!-- capsule-v2 -->
# SDK duplicate control_response dedup — how do you stop redelivered permission responses from corrupting the conversation?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When a transport can re-deliver control responses after reconnect, what dedup structure prevents duplicate tool results from reaching the API?

## Resolved-ID Set with insertion-order eviction
**Path/Symbol:** `src/cli/structuredIO.ts`: `MAX_RESOLVED_TOOL_USE_IDS`/:130-133, `resolvedToolUseIds` field/:149-155, `trackResolvedToolUseId`/:172-187, orphan handling in `processLine`/:362-398.
**Signature:** `trackResolvedToolUseId(request: SDKControlRequest): void` — records ONLY `can_use_tool` subtypes; Set eviction takes `values().next().value` (Sets iterate in INSERTION ORDER = oldest first).
**Data Shape:** key = the tool_use_id INSIDE the control_request/response payload — not the request_id — because redelivery pairing is per tool call.

### Decisive source
```ts
// Tracks tool_use IDs that have been resolved through the normal permission
// flow (or aborted by a hook). When a duplicate control_response arrives
// after the original was already handled, this Set prevents the orphan
// handler from re-processing it — which would push duplicate assistant
// messages into mutableMessages and cause a 400 "tool_use ids must be unique"
// error from the API.
private readonly resolvedToolUseIds = new Set<string>()
```
```ts
const request = this.pendingRequests.get(message.response.request_id)
if (!request) {
  // Duplicate control_response deliveries (e.g. from WebSocket reconnects)
  // arrive after the original was handled...
  const toolUseID = responsePayload?.toolUseID
  if (typeof toolUseID === 'string' && this.resolvedToolUseIds.has(toolUseID)) {
    logForDebugging(`Ignoring duplicate control_response for already-resolved ...`)
    return undefined
  }
  if (this.unexpectedResponseCallback) await this.unexpectedResponseCallback(message)
  return undefined
}
```

**Flow:** every resolution path calls trackResolvedToolUseId BEFORE the pending entry disappears: normal control_response (:400), abort listener (:501), injectControlResponse (:288). Late duplicates then find NO pending request but DO find the resolved ID ⇒ silently ignored instead of forwarded to the orphan/unexpected-response path. Lifecycle close (`notifyCommandLifecycle(uuid,'completed')` :362-373) fires for EVERY control_response INCLUDING duplicates and orphans — orphans never yield to print.ts's main loop, so processLine is the only code that ever sees them.
**Invariant:** The cap (1000) trades unbounded memory in very long sessions for a tiny window where an ancient duplicate could slip through — acceptable because redelivery windows are short relative to 1000 resolutions. Track-BEFORE-delete ordering matters: resolution bookkeeping must land while both maps can still be updated atomically in one synchronous block. Unknown request_id + unresolved tool_use_id ⇒ unexpectedResponseCallback (bridge cancels its stale UI prompt); with neither, the response is dropped silently.
**Probe:** `grep -n "tool_use ids must be unique" src/cli/structuredIO.ts` (`:153` comment), `grep -n "MAX_RESOLVED_TOOL_USE_IDS = 1000" src/cli/structuredIO.ts` (`:133`), `grep -n "Ignoring duplicate control_response" src/cli/structuredIO.ts` (`:391`), `grep -n "notifyCommandLifecycle(uuid, 'completed')" src/cli/structuredIO.ts` (`:372`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "control_response duplicate resolved tool_use orphan pending request resolve schema", limit: 6 });
// rank#1 trackResolvedToolUseId :176-187 · injectControlResponse :283-309 (executed live pre-write)
```

## Verdict
Adopt for ANY client that multiplexes permission/RPC decisions over a redeliverable channel. Adapt the key to your idempotency identity (request_id vs payload id). Omit eviction only for bounded sessions; never omit the track-before-delete ordering.
