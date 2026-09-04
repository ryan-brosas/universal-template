<!-- capsule-v2 -->
# Read-only/write batch partitioning — how are concurrent tool calls made safe without locks?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Which tools may run in parallel within one assistant turn, where do context mutations apply, and what happens when safety classification itself throws?

## runTools + partitionToolCalls
**Path/Symbol:** `src/services/tools/toolOrchestration.ts:runTools` (:19-82), `partitionToolCalls` (:91-116), `runToolsConcurrently` (:152-177), `runToolsSerially` (:118-150); concurrency cap `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || 10` (:8-12).
**Signature:** `async function* runTools(toolUseMessages: ToolUseBlock[], assistantMessages, canUseTool, toolUseContext): AsyncGenerator<MessageUpdate, void>` with `MessageUpdate = { message?: Message; newContext: ToolUseContext }`.
**Data Shape:** batches = consecutive runs of concurrency-safe calls (`{isConcurrencySafe: boolean; blocks: ToolUseBlock[]}`); safety comes from `tool.inputSchema.safeParse(input)` THEN `tool.isConcurrencySafe(parsed.data)`.

### Decisive source
```ts
const isConcurrencySafe = parsedInput?.success ? (() => {
  try { return Boolean(tool?.isConcurrencySafe(parsedInput.data)) }
  catch { // If isConcurrencySafe throws (e.g., due to shell-quote parse failure),
          // treat as not concurrency-safe to be conservative
    return false } })() : false
if (isConcurrencySafe && acc[acc.length-1]?.isConcurrencySafe) acc[acc.length-1].blocks.push(toolUse)
else acc.push({ isConcurrencySafe, blocks: [toolUse] })
// concurrent batch: contextModifiers are QUEUED per toolUseID and applied in
// BLOCK ORDER after the whole batch completes — never mid-batch
```

**Flow:** partition order-preserving → read-only batches run through `all(generators, maxConcurrency)` with in-progress-ID bookkeeping (add on start, delete on complete) → each generator's `contextModifier` updates are COLLECTED during the batch and replayed sequentially after it finishes (yielding `{newContext}` once) → write/unsafe batches run strictly serially with modifiers applied immediately between tools → results stream out as they finish regardless of batching.
**Invariant:** (1) classification failure degrades to SERIAL — conservative-by-default beats availability; (2) context mutation ordering is deterministic even when execution isn't: queued modifiers apply in original call order after the batch (two parallel writes to context can't interleave); (3) a single non-read-only tool always forms its own batch — write isolation needs no locks because nothing else runs alongside; (4) `setInProgressToolUseIDs` uses functional setState copies (never mutate prev Set).
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "partitionToolCalls\|queuedContextModifiers" src/services/tools/toolOrchestration.ts`; `grep -rn "isConcurrencySafe" src/Tool.ts src/tools/*/[A-Z]*Tool.ts | head` shows per-tool predicates; graph resolves runTools :19-82 + partitionToolCalls :91-116 line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "runTools partitionToolCalls concurrency safe batch", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt consecutive-run partitioning + deferred modifier replay; adapt the per-tool predicate surface; omit the streaming executor twin if your host executes post-stream only. Porting trap: applying contextModifiers as they arrive during a concurrent batch introduces nondeterministic context state depending on completion order.
