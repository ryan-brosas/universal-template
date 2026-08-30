<!-- capsule-v2 -->
# ACP stream translator — how do you MANUFACTURE step/block structure for a protocol that only emits flat session updates?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** when a wire protocol has no text-block or step concept, where do block ids come from, when may a tool call be withheld, and who closes a step the protocol never opened?

## Inference-based translation kernel (`createACPStreamTranslator`)
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/stream-translator.ts:createACPStreamTranslator` (:33–408).
**Signature:** `({ emit, emitToolCallCandidate?, builtinTools? }) => { update, permissionToolCall, raw, close, finish, hostToolCall, hostToolResult }`.
**Data Shape:** per-instance state = `openBlock {type,id,messageId}`, `blockCounter`, `stepOpen`, `finished` latch, `blockIdCounts` Map, `toolStates` Map (per toolCallId merge buffer), `pendingToolCallIds` Set. Every session update ALSO emits a lossless `{type:'raw'}` part BEFORE its translation (`update()` :324–327; bare-argument form defaults `preserveRaw:true`).

### Decisive source
```ts
// :109–138 — blocks coalesce on BOTH type and messageId
if (
  openBlock == null ||
  openBlock.type !== type ||
  openBlock.messageId !== normalizedMessageId   // changed id forces a new block even at equal type
) {
  closeBlock();
  const id = createBlockId({ type, messageId: normalizedMessageId });
  emit({ type: type === 'text' ? 'text-start' : 'reasoning-start', id });
  openBlock = { type, id, messageId: normalizedMessageId };
}
// :96–107 — ids preserve provider messageIds with -N collision suffixes
const base = messageId ?? `acp-${type}-${++blockCounter}`;
const count = (blockIdCounts.get(base) ?? 0) + 1;
return count === 1 ? base : `${base}-${count}`;
```

**Flow:** text/thought chunks coalesce into open blocks keyed `(type, messageId)` → tool_call updates merge into a per-id state (`mergeToolUpdate` :656–691 keeps only present-and-defined properties; programmatic `name` read from the RAW update) → pending+unemitted calls are HELD BACK (:192–199) unless `forceEmit` (permission path :366–372) → builtin tools re-identify through a three-source ladder (`resolveBuiltinTool` :478–509): programmatic name → recursive `_meta` walk matching `name`/`toolName` strings with cycle guard (:511–543) → UNIQUE inputSchema shape match where every required property must be present AND const/single-member-enum discriminators must match (:545–607); an unknown metadata name BLOCKS the schema fallback (:499–503) → recognized builtin with an inputSchema WAITS until required input arrives instead of emitting a skeleton (:213–224) → unrecognized calls get sanitized dynamic names ([^A-Za-z0-9_-]→`_`, trimmed, ≤128, letter-prefix else `acp_`, :804–818) and fire `emitToolCallCandidate` so the adapter can classify MCP-origin calls (:236) → when the last pending call settles while a step is open, emit `finish-step {unified:'tool-calls', harnessMetadata.acp.inferredStep:true}` (:140–165) → `finish(response)` is exactly-once (`finished` latch), emits the raw response, closes any still-open step with the REAL stop reason, then emits `finish` (:379–406).

**Invariant:** consumers NEVER see unclosed blocks or fabricated skeletons — `close()` synthesizes missing `-end`s (:87–94), a builtin whose schema requires input stays silent until that input arrives, and `mapACPFinishReason` (:410–431) maps `end_turn→stop`, `max_tokens|max_turn_requests→length`, `refusal→content-filter`, everything else (incl. `cancelled`)→`other` while always retaining the raw reason. Host-relayed calls ride the same pump with `providerExecuted:false` (:270–312) and share `pendingToolCallIds`, so parallel host calls close their step only after ALL results.

**Probe:** `packages/harness-acp/src/v1/bridge/stream-translator.test.ts` — `:731–867` pins parallel-vs-serial inferred steps (0 finish-steps until BOTH parallel calls settle, then one per serial call); `:1011–1090` pins a terminal step closed with the real reason (`max_tokens→length`) even when the tool never settles plus second-finish no-op; `:452–523` pins const-discriminator shape matching distinguishing anonymous tools.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "ACP stream translator session update text thought tool call block coalesce", limit: 10 });
```
Live @pin: rank#1 `stream-translator.update :315-365`, then `emitToolUpdate :167-268`, `mergeToolUpdate :656-691`; `trace_path(createACPStreamTranslator)` callers_total=2 (createEmitStreamEvent hop-1 wraps EVERY stream emission; runTurn hop-2 owns the translator).

## Verdict
Adopt inference-based translation: raw-first passthrough for losslessness, (type,messageId)-keyed blocks with collision-suffix ids, three-source builtin re-identification with unique-match-only, hold-back-until-input, inferred steps flagged in harnessMetadata, and the exact-once finish with real-reason step closure. Adapt stopReason vocabularies and builtin-mapping sources to your dialect. Omit ACP-specific `_meta.claudeCode` shapes and the file-change projection from diff content (:747–802) unless your runtime reports diffs the same way. Coverage caveat: runner block stands (no node_modules → vitest unrunnable); all Probe anchors verified by direct reads at pin.
