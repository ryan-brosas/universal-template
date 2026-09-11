<!-- capsule-v2 -->
# Host-tool correlation window — how do you suppress the DUPLICATE of a tool call you already displayed, without ever losing a call?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** when one logical invocation produces BOTH a relay-side emission and the agent's own announcement, which evidence justifies dropping the echo — and what happens to unmatched echoes?

## Exactly-once display kernel (`createHostToolCorrelation`)
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/host-tool-correlation.ts:createHostToolCorrelation` (:35–262).
**Signature:** `({ emitSemanticUpdate, emitRawUpdate, hostToolServerName, hostTools }) => { update, registerInvocation, claimHostToolPermission, flush, removeInvocation, close }`.
**Data Shape:** constants `CORRELATION_WINDOW_MS = 1000`, `MAX_BUFFERED_UPDATES = 128` (:32–33); state = `invocations` Map(token→{token, serverName, toolName, inputFingerprint, order, expiryTimer?, toolCallId?}), `candidates` Map(toolCallId→{order, evidence[]}), `suppressedToolCallIds` Set, `releasedToolCallIds` Set, bounded `buffered` array + single unref'd flush timer.

### Decisive source
```ts
// :343 — portable evidence requires ALL THREE signals
return hasServerIdentity && hasToolName && hasInput;
// :157–164 — suppressed ids stay silent until their TERMINAL update lifts suppression
if (suppressedToolCallIds.has(toolCallId)) {
  if (isTerminalToolUpdate(message)) {          // status 'completed' | 'failed'
    suppressedToolCallIds.delete(toolCallId);
    removeInvocationForToolCall({ invocations, toolCallId });
  }
  return;                                        // non-terminal echo: dropped
}
```

**Flow:** raw values are ALWAYS forwarded first (`emitRawUpdate` :146) — suppression touches only the SEMANTIC stream → tool updates that match nothing buffer with their evidence (semantic update + preserved raw push both onto `candidate.evidence` :180); token evidence is EXACT containment of the 64-hex correlation token (minted by the relay, returned inside the MCP result `_meta['ai-sdk-harness-acp-correlation']`, echoed in the agent's announcement) checked bidirectionally — candidate→invocation at update time (:183–189) and registration→buffered-candidates scan (:208–215) → without a token, `reconcile()` pairs unmatched invocations↔candidates in FIFO `order` via `hasPortableEvidence`: server identity (delimited `server__tool` boundary-aware pair :431–470 or exact server string), tool name, and canonical-JSON INPUT FINGERPRINT found recursively (:264–344, :552–597) — ALL THREE must hold → registered invocations expire after CORRELATION_WINDOW_MS (unref'd timer :203–207), bounding how long an announcement can still be correlated → buffered updates flush in ORIGINAL order when the window closes, the buffer hits 128, candidates empty, or `close()` runs (:70–96).

**Invariant:** fail-open to duplication, never to loss — unmatched candidates FLUSH verbatim after the window (:90–95), title-only candidates are never suppressed (no identity/fingerprint ⇒ no portable evidence; test :366–387), and `claimHostToolPermission` reuses the same matcher but requires EXACTLY ONE host-tool match else returns false so ambiguity degrades to letting the consumer see the native request (:218–244). The relay's 409/404 gates never consume order (relay capsule), keeping FIFO pairing dense.

**Probe:** `packages/harness-acp/src/v1/bridge/host-tool-correlation.test.ts` — `:10–42` ACP-before-MCP pairing incl. key-order-independent fingerprint ({unit,city} vs {city,unit}); `:70–95` result-token strongest-evidence match where registration happens AFTER the notification arrived; `:335–364` window flush restores original order; `:480–508` expired invocation stops correlating late echoes.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "correlation suppress duplicate tool call announcement buffered window fingerprint", limit: 10 });
```
Live @pin: rank#1 `suppressToolCallUpdate :117-121`; `trace_path(createHostToolCorrelation)` callers_total=2 — `createEmitStreamEvent` wraps EVERY stream emission through the suppressor and `runTurn` registers relay invocations.

## Verdict
Adopt: raw-always/semantic-suppressed split, two-tier evidence (exact token > three-signal portable), FIFO reconcile, terminal-lifts-suppression, bounded window+buffer, exactly-one permission claim. Adapt the delimited-pair grammar (`server__tool`) and deferred-tool envelope (`rawInput.tool_name/tool_input`) to your naming scheme. Omit nothing load-bearing — every branch above is pinned by tests. Coverage caveat: runner block stands (no node_modules → vitest unrunnable); all anchors verified by direct reads at pin.
