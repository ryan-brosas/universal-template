<!-- capsule-v2 -->
# Relevant-memory prefetch — how do semantic memories ride along a turn with zero added latency?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the start-early / consume-if-settled / dispose-everywhere lifecycle for side-query context injection.

## MemoryPrefetch
**Path/Symbol:** `src/utils/attachments.ts:MemoryPrefetch` (:2346-2353), `startRelevantMemoryPrefetch` (:2361-2424), `getRelevantMemoryAttachments` (:2196-2242); consume site `src/query.ts:301` (`using pendingMemoryPrefetch = …`) and `:1600-1621`.
**Signature:** `(messages, toolUseContext) → MemoryPrefetch | undefined`; handle = `{ promise, settledAt: number | null, consumedOnIteration: number, [Symbol.dispose](): void }`.
**Data Shape:** gates — auto-memory enabled AND statsig flag `tengu_moth_copse`, last real user message exists (`findLast(!isMeta)`), prompt has whitespace (single words skipped), session byte budget not exhausted.

### Decisive source
```ts
const promise = getRelevantMemoryAttachments(
  input, agents, readFileState,
  collectRecentSuccessfulTools(messages, lastUserMessage),
  controller.signal, surfaced.paths,
).catch(e => { if (!isAbortError(e)) logError(e); return [] })
const handle: MemoryPrefetch = {
  promise, settledAt: null, consumedOnIteration: -1,
  [Symbol.dispose]() {           // query.ts binds with `using`
    controller.abort()
    logEvent('tengu_memdir_prefetch_collected', { hidden_by_first_iteration:
      handle.settledAt !== null && handle.consumedOnIteration === 0,
      latency_ms: (handle.settledAt ?? Date.now()) - firedAt })
  },
}
void promise.finally(() => { handle.settledAt = Date.now() })
```

**Flow:** fired ONCE per user turn before the loop (prompt invariant across iterations) → runs concurrently with model streaming + tool execution → at each post-tools collect point the loop polls: consume only if `settledAt !== null && consumedOnIteration === -1`, else skip-and-retry-next-iteration ("zero-wait; as many chances as there are loop iterations") → `filterDuplicateMemoryAttachments(await promise, readFileState)` then mark `consumedOnIteration`. Child abort controller chained to the turn's controller so Escape cancels immediately; `using` disposes on ALL generator exit paths (~13 return sites — no per-site instrumentation).
**Invariant:** the prefetch NEVER blocks the turn; consumption is idempotent via the `-1` sentinel; selection inputs are transcript-scanned (`collectSurfacedMemories` paths+bytes reset naturally on compact because scanned attachments are gone from the compacted transcript); recent-successful-tools suppression ("any error → excluded; no result yet → excluded") keeps docs for working tools out of context.
**Probe:** no upstream test (coverage caveat). Deterministic probe: `grep -n "using pendingMemoryPrefetch\|consumedOnIteration" src/query.ts` pins both ends of the lifecycle.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "MemoryPrefetch settledAt consumedOnIteration startRelevantMemoryPrefetch", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt disposable-handle prefetch + settle-poll consumption + child-abort chaining; adapt the selector behind it; omit AKI/Haiku specifics. Porting trap: awaiting the prefetch at collect time converts "free" context into head-of-line blocking on every slow side-query; forgetting the consumed-flag lets duplicate memory blocks enter on consecutive iterations.
