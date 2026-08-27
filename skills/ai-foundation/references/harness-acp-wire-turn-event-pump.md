<!-- capsule-v2 -->
# ACP wireTurn event pump — how does a host-side turn forward bridge events without ever delivering an unclosed text/reasoning block?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the runtime can die mid-block, how do you guarantee consumers see balanced start/end pairs, one-shot classification of dynamic tools, and correct settle semantics for abort/suspend/error?

## Open-block tracking + settle-once done promise
**Path/Symbol:** `packages/harness-acp/src/v1/acp-v1-harness.ts` — `wireTurn` (:1038–1229): openBlock tracker (:1057–1087), classification maps (:1060–1061, :1125–1163), settle (:1107–1124), terminal subscriptions (:1167–1197), PromptControl return (:1210–1228).
**Signature:** `wireTurn({emit, abortSignal?, start}): HarnessV1PromptControl` where control = `{submitToolApproval(input), submitToolResult(input), done: Promise<void>}`.
**Data Shape:** per-turn locals — `openBlock {type:'text'|'reasoning', id} | undefined`; `dynamicToolCalls Map<toolCallId, boolean>`; `toolCallClassificationErrors Map<toolCallId, unknown>`; `settled`/`abortRequested`/`abortError`.

### Decisive source
```ts
// acp-v1-harness.ts:1063–1087 — track the open block so ANY exit can close it
const forward = (event) => {
  if (event.type === 'text-start' || event.type === 'reasoning-start') {
    openBlock = { type: event.type === 'text-start' ? 'text' : 'reasoning', id: event.id };
  } else if ((event.type === 'text-end' || event.type === 'reasoning-end') && openBlock?.id === event.id) {
    openBlock = undefined;
  }
  try { emit(event); } catch {}
};
const closeForwardedBlock = () => {
  if (openBlock == null) return;
  const block = openBlock; openBlock = undefined;
  forward({ type: block.type === 'text' ? 'text-end' : 'reasoning-end', id: block.id });
};
// :1138–1154 — dynamic classification decided ONCE at candidate time; a throw in
// isMcpToolCall surfaces as an error part + abort when the tool-call arrives
channel.on('tool-call', event => {
  if (toolCallClassificationErrors.has(event.toolCallId)) {
    const error = toolCallClassificationErrors.get(event.toolCallId);
    closeForwardedBlock(); forward({ type: 'error', error });
    try { channel.send({ type: 'abort' }); } catch {}
    settle({ error }); return;
  }
  forward(dynamicToolCalls.get(event.toolCallId) === true ? { ...event, dynamic: true } : event);
});
// :1185–1189 — a 'suspended' close IS success (slice boundary, not failure)
channel.onClose((_code, reason) => {
  if (reason === 'suspended') { settle({}); return; } ...
});
```

**Flow:** wireTurn subscribes to the fixed event-type list plus terminal channels → every forwarded event updates the open-block pair → on finish/error/close `closeForwardedBlock()` synthesizes the missing end BEFORE forwarding the terminal → `settle` resolves/rejects the done promise exactly once and unsubscribes everything (including the abort listener) → user abort sends `{type:'abort'}` immediately and settles with the stored abort error when finish arrives; close reason `'suspended'` settles SUCCESS because the next process replays the tail.
**Invariant:** consumers must never observe an unclosed text/reasoning block regardless of how the stream dies; tool-call dynamicity is decided exactly once per id at candidate time and a throwing classifier becomes an error part + abort, never a silent misclassification; after settle, no late channel events can re-enter consumer code.
**Probe:** direct tests `packages/harness-acp/src/acp-harness.test.ts:2040–2045` (`events.map(type)` equals exactly `['text-start','text-delta','text-end','finish']`), :3277+ ("waits for the bridge terminal sequence after cancellation before rejecting the turn"), suspend/resume cursor case :2285–2368 (suspended close resolves done). Note the pump itself has no dedicated unit file — behavior pinned via adapter integration cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "wireTurn closeForwardedBlock dynamicToolCalls submitToolApproval submitToolResult", limit: 10 });
```

## Verdict
Adopt open-block tracking + synthesized closes as a transport-independent consumer guarantee; adapt the event vocabulary and the classification hook signature; omit ACP frame names. Caveat: pinned through adapter tests rather than a dedicated wireTurn suite.
