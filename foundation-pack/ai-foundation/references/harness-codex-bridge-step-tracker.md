<!-- capsule-v2 -->
# Codex bridge step tracker + event translation — how do you manufacture harness steps and text parts from a runtime that streams items, not steps?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the sandboxed runtime's event vocabulary is item-based (started/updated/completed) with no step concept, how does the bridge infer step boundaries and keep text/reasoning parts well-formed against an unreliable start-event contract?

## Two-item-class step inference with a pending-tool gate
**Path/Symbol:** `packages/harness-codex/src/bridge/codex-step-tracker.ts` — `createCodexStepTracker` (:22–61), `finishStep` (:28–38), `isModelStepItem` (:67–69), `isToolStepItem` (:71–79), `defaultUsage` (:81–86).
**Signature:** `createCodexStepTracker({send: Emit}): { observeEvent({event, itemId}): void; finishTurn(): void }`.
**Data Shape:** model items = `reasoning` | `agent_message` (open a step, never close it); tool items = `command_execution` | `mcp_tool_call` | `web_search` | `file_change` | `todo_list` (track itemId in/out); emitted finish-step carries `harnessMetadata: { codex: { inferredStep: true } }` and zeroed usage — real usage rides the separate `turn.completed` event.

### Decisive source
```ts
// codex-step-tracker.ts:28–38 — a step closes ONLY when open AND no tool item
// is still pending
const finishStep = (): void => {
  if (!stepOpen || pendingToolItemIds.size > 0) return;
  input.send({
    type: 'finish-step',
    finishReason: { unified: 'stop', raw: 'stop' },
    usage: defaultUsage(),
    harnessMetadata: { codex: { inferredStep: true } },
  });
  stepOpen = false;
};
// :46–53 — model items open; tool items add on item.started, remove + try-close
// on item.completed
if (isToolStepItem(item)) {
  if (event.type === 'item.started' && itemId) {
    pendingToolItemIds.add(itemId);
  } else if (event.type === 'item.completed') {
    if (itemId) pendingToolItemIds.delete(itemId);
    finishStep();
  }
  return;
}
```

**Flow:** every non-suppressed item event is observed → a reasoning/agent_message item sets `stepOpen=true` → each tool item registers its id on started and removes it on completed, attempting a close after every removal → `turn.completed` calls `finishTurn()`, which clears any still-pending ids and force-closes, so a turn always ends with its last step closed even if the runtime never completed a tool item.
**Invariant:** consumers NEVER see an unclosed step or a finish-step while a tool item is still in flight — the pending set is the gate, and finishTurn's clear-then-close makes the terminal boundary total.

## Lazy-open prefix-diff text parts
**Path/Symbol:** `packages/harness-codex/src/bridge/create-emit-stream-event.ts` — `createEmitStreamEvent` (:59–251), agent_message branch (:112–131), reasoning branch (:136–150), `NATIVE_TO_COMMON` (:50–53), `mapUsage` (:274–289), `extractMcpToolCallResult` (:253–272).
**Signature:** `createEmitStreamEvent({send, stepTracker, setTurnUsage, setThreadId, emitWarning, emitError}): (event: CodexEvent) => void`.
**Data Shape:** per-item accumulated text maps (`textByItem`, `reasoningByItem`) keyed by item id (synthetic `randomUUID()` when absent); deltas are pure prefix growth; native-name remap table has exactly two entries (`shell→bash`, `web_search→webSearch`) — all other names forward as-is, MCP calls additionally get `dynamic:true`; usage maps `cached_input_tokens` into `cacheRead` with `noCache = max(0, total - cacheRead)` and `cacheWrite: 0`.

### Decisive source
```ts
// create-emit-stream-event.ts:113–121 — presence-in-map marks "opened", NOT
// the item.started event: Codex does not guarantee a started-with-text
// precedes the first updated-with-text
if (!textByItem.has(id)) {
  send({ type: 'text-start', id });
  textByItem.set(id, '');
}
const last = textByItem.get(id) ?? '';
const next = item.text;
if (next.length > last.length) {
  send({ type: 'text-delta', id, delta: next.slice(last.length) });
  textByItem.set(id, next);
}
if (event.type === 'item.completed') send({ type: 'text-end', id });
```

**Flow:** `thread.started` stores the thread id AND announces `bridge-thread` to the host (the resume-state carrier) → item events translate per type: agent_message/reasoning accumulate with lazy open + prefix-diff deltas + end-on-completed; command_execution/web_search emit providerExecuted tool-call on started and tool-result on completed; mcp_tool_call emits dynamic tool pairs with structured_content-preferred result extraction; file_change expands to one file-change part per change (add→create, delete→delete, update→modify); error ITEMS degrade to emitWarning while turn.failed/error route to emitError → `turn.completed` captures mapped usage and closes the final step.
**Invariant:** no text-delta can ever be emitted for a part whose text-start was not already sent (the map-presence gate makes this structural, not ordering-dependent); a shrinking or rewritten text payload emits nothing rather than a negative delta; every consumer-visible tool call/result pair keeps the same toolCallId across its two halves.
**Probe:** `packages/harness-codex/src/bridge/codex-step-tracker.test.ts` (136L, 5 cases): model-text step stays open until finishTurn; tool completion closes; pending tool blocks close across an interleaved agent_message; force-close of a dangling pending tool at turn end; two finish-steps for tool-step-then-final-text. `packages/harness-codex/src/bridge/create-emit-stream-event.test.ts` (248L, 3 snapshot cases): bridge-thread + lazy-open accumulated text ('hello' then ' world' delta) + usage mapping (input 5 / cached 2 ⇒ noCache 3); reasoning accumulation; command + MCP translation with structured_content preference.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createCodexStepTracker createEmitStreamEvent inferredStep textByItem mapUsage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-item-class step inference (openers vs closers with a pending-id gate + terminal force-close) for any item-based runtime lacking steps; adopt lazy-open-by-map-presence + prefix-diff deltas whenever the upstream start-event contract is unreliable; adopt the tiny explicit native→common name table (forward unknowns, mark dynamic) over exhaustive remaps; adapt the item-type lists, metadata tag, and usage field names per runtime; omit per-item synthetic UUIDs only if your runtime guarantees ids. Caveat: the relay-command suppression path around these translators (index.ts :235–253) is deterministic-read-only — no test drives a full relay command through runTurn.
