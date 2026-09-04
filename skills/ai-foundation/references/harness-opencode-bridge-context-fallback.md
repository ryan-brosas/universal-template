<!-- capsule-v2 -->
# OpenCode bridge context fallback — when the event stream settles without streamed assistant content, how do you recover the response from the runtime's own store without emitting a stale message?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A turn can settle (busy→idle, error, stream end) without the bridge ever seeing a finish-step — the runtime answered but the events were missed or never streamed. How do you fetch the real answer afterwards and prove it belongs to THIS prompt?

## Baseline correlation: existed / id / changed
**Path/Symbol:** `packages/harness-opencode/src/bridge/opencode-context-fallback.ts` — `createAssistantSnapshotBaseline` (:6–13), `isAssistantSnapshotAfterBaseline` (:15–25); `packages/harness-opencode/src/bridge/index.ts` — `emitContextFallback` (:1177–1230), `latestAssistantSnapshot` (:1257–1275), `latestLegacyAssistantMessage` (:1277–1298), `latestV2AssistantMessage` (:1300–1328), `emitAssistantContentPart` (:1330–1348).
**Signature:** `isAssistantSnapshotAfterBaseline({assistant: {id?: unknown}, baseline: AssistantSnapshotBaseline}): boolean`; `emitContextFallback({client, sessionId, assistantBaseline, state, emit, emitContent}): Promise<boolean>`.
**Data Shape:** baseline = `{assistantExisted: boolean; assistantId?: string}` captured BEFORE the prompt from the latest assistant snapshot; snapshot = `{id?, contentParts?, tokens?, finish?, cost?, error?, model?, providerID?, modelID?, metadata?}`; `emitContent` = `!sawContent` (re-emit text only when nothing streamed at all).

### Decisive source
```ts
// opencode-context-fallback.ts:15–25 — the correlation test is three-way and
// fails CLOSED on missing ids
export function isAssistantSnapshotAfterBaseline({
  assistant,
  baseline,
}: {
  assistant: { id?: unknown };
  baseline: AssistantSnapshotBaseline;
}): boolean {
  if (typeof assistant.id !== 'string') return false;
  if (!baseline.assistantExisted) return true;
  return baseline.assistantId != null && assistant.id !== baseline.assistantId;
}
```
```ts
// index.ts:1192–1201 — re-fetch AFTER settlement; only an after-baseline
// snapshot may be emitted
const assistant = await latestAssistantSnapshot({ client, sessionId });
if (
  !assistant ||
  !isAssistantSnapshotAfterBaseline({
    assistant,
    baseline: assistantBaseline,
  })
) {
  return false;
}
```

**Flow:** before the prompt, `createAssistantSnapshotBaseline(await latestAssistantSnapshot(...))` records whether an assistant message already existed and its id → after an uncorrelated settlement (`!sawFinishStep`), `emitContextFallback` re-fetches the latest snapshot (legacy `client.session.messages({limit: 20})` scanned backwards for `role==='assistant'` FIRST, then v2 `client.v2.session.context` scanned for `type==='assistant'`) → if not after-baseline, return false (the caller then throws) → otherwise emit `stream-start` via `emitOpenCodeStreamStart`, re-emit each text/reasoning content part as start/delta/end (synthetic id `${type}-${randomUUID()}` when the part has none) ONLY when `emitContent`, then a `finish-step` with `mapOpenCodeFinishReason(assistant.finish ?? (assistant.error ? 'error' : 'stop'))`, `mapUsage(assistant.tokens)`, and `harnessMetadata.opencode = {cost?, fallback: true}`.
**Invariant:** a pre-prompt assistant message can NEVER be emitted as this turn's answer (same-id ⇒ rejected); a snapshot without a usable id is never trusted (fail closed) even when no prior assistant existed; the fallback is marked in metadata so consumers can tell recovered content from streamed content.
**Probe:** `packages/harness-opencode/src/bridge/opencode-context-fallback.test.ts` (44L, 3 cases): rejects the assistant that existed before the prompt (same id ⇒ false); accepts a new assistant id (⇒ true); fails closed when an existing assistant has no usable id (baseline `{}` + new id ⇒ false).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "emitContextFallback isAssistantSnapshotAfterBaseline latestAssistantSnapshot createAssistantSnapshotBaseline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capture-baseline-before / correlate-after pattern for any recovery-from-store fallback where the store accumulates across turns; adopt fail-closed-on-missing-id (an unidentifiable existing record must block recovery, not enable it); adopt the two-source snapshot fetch (legacy endpoint first, versioned endpoint second) only while supporting both API generations; adapt the "after" predicate to your store's identity scheme (monotonic sequence numbers work too) and the re-emission part types to your stream vocabulary. Caveat: the wiring site in runPrompt (:734–748) is deterministic-read-only — the kernel is fully test-pinned, the call path is not.
