<!-- capsule-v2 -->
# EngineResult projection — how does SDK history/usage become the runtime's wire-shaped result without ever throwing?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter must convert a vendor SDK's opaque history and usage blobs into a stable runtime schema at stream settle — what is mapped, what is dropped, and what is merged into usage?

## sdkHistoryToRuntime + normalizeUsage + route merge
**Path/Symbol:** `agent-runtime/src/sdk-engine.ts` — `sdkHistoryToRuntime` (:572-600) with `extractText` (:602-608); `normalizeUsage` (:706-714) with `compactObject`/`numberValue` (:716-722); final merge in `consumeStream` (:364-375).
**Signature:** `sdkHistoryToRuntime(history: unknown): RuntimeHistoryItem[]`; `normalizeUsage(usage: unknown): RuntimeUsage`.
**Data Shape:** History items: `{id, kind: "message"|"reasoning"|"tool_call"|"tool_result", role?, text?, callId?, groupId?, payload}`. Usage: `{inputTokens?, outputTokens?, totalTokens?, requests?}` all optional finite numbers, plus `route?` and `resolvedModel?` from the model provider.

### Decisive source
```ts
const id = typeof item.id === "string" ? item.id : `sdk-history-${index}-${crypto.randomUUID()}`;
if (typeof item.role === "string") {
  const text = extractText(item.content);          // string | join(part.text for parts)
  return [{ id, kind: "message", role, text, payload }];
}
const kind = itemType.includes("reasoning") ? "reasoning"
  : itemType.includes("output") || itemType.includes("result") ? "tool_result"
  : itemType.includes("call") ? "tool_call" : undefined;
if (!kind) return [];                              // UNKNOWN item kinds are DROPPED
return [{ id, kind, ...(callId ? { callId, groupId: callId } : {}), payload }];

// usage: camel OR snake accepted; non-finite → key omitted entirely
inputTokens: numberValue(usage.inputTokens ?? usage.input_tokens), ...
// consumeStream merge:
usage: { ...normalizeUsage(stream.usage), ...modelProvider.latestRoute,
         ...(modelProvider.resolvedModel ? { resolvedModel: ... } : {}) }
```

**Flow:** stream completes → history array flattened item-by-item (role-bearing records become messages with joined text; type-substring classification buckets the rest as reasoning/tool_call/tool_result; anything unclassifiable vanishes rather than crashing the settle path) → usage normalized tolerantly → provider route info and the Auto-resolved concrete model are spread on top so the host can persist routing decisions with the result.
**Invariant:** Conversion NEVER throws on hostile/morphing SDK shapes (non-arrays → `[]`, missing ids get synthetic unique ones, unknown kinds dropped silently) — settle-path robustness outranks completeness; tool_call/tool_result items carry `groupId = callId`, which is exactly the key compaction later uses to keep pairs atomic (round-trip test proves a persisted group replays as proper assistant `tool_calls` + `tool` message with matching `tool_call_id`). Usage keys are omitted, never null or NaN.
**Probe:** `agent-runtime/test/sdk-tool-loop.test.ts` "replays a persisted tool group into the next model turn" (:450-545, asserts `groupId: "call-1"` items replay with `tool_call_id === "call-1"` and exact output content). Coverage caveat: this probe pins the RUNTIME→SDK replay direction plus the group-key contract; the SDK→runtime direction of `sdkHistoryToRuntime` itself has no dedicated direct test — source-only claim. Suite runner-blocked at pin.

## Get live surrounding code
**Retrieve:** executed at pin:
```
search_graph({ project:"os-clovy", query:"sdk history runtime items usage normalize", file_pattern:"agent-runtime/src/*" })
→ src.sdk-engine.normalizeUsage Function sdk-engine.ts 706-714        (rank 1)
   src.sdk-engine.sdkHistoryToRuntime Function sdk-engine.ts 572-600
   src.sdk-engine.historyToSdkInput Function sdk-engine.ts 492-521
```

## Verdict
Adopt fail-soft total conversion (drop-don't-throw), groupId=callId on tool items, and camel/snake-tolerant finite-only usage with route/resolvedModel merged at the result boundary. Adapt the kind taxonomy to your history schema but keep a group key bridging calls to results. Omit nothing structural; if your SDK guarantees richer item types, map them explicitly instead of widening the substring ladder.
