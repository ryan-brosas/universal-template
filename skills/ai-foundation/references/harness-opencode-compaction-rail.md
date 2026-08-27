<!-- capsule-v2 -->
# OpenCode compaction rail — how do compaction events that happen outside any active turn reach the next turn's consumer in order?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A runtime can compact its context BETWEEN turns, when no consumer stream is attached — how do those compaction parts survive and arrive before the next turn's first event?

## Out-of-turn buffering + flush-at-next-wireTurn
**Path/Symbol:** `packages/harness-opencode/src/opencode-harness.ts` — `pendingCompactionParts` (:799), `doCompact` (:1039–1064), `runCompactOperation` (:1211–1260), flush at wireTurn entry (:916–918), `'compaction'` in eventTypes (:843); protocol side `operation: z.enum(['prompt','compact'])` in `opencode-bridge-protocol.ts` startMessageSchema (:11).
**Signature:** `doCompact(customInstructions?: string): Promise<void>`; `runCompactOperation({channel, model, provider, permissionMode, debug, mcpServers, resumeSessionId, onCompaction}): Promise<void>`.
**Data Shape:** session-scoped `pendingCompactionParts: HarnessV1StreamPart[]` (empty at rest); the compact operation sends `start {operation:'compact', prompt:'', tools:[], model, provider?, mcpServers?, permissionMode?, resumeSessionId?, debug?}`.

### Decisive source
```ts
// opencode-harness.ts:1039–1063 — two gates, then a buffered operation
doCompact: async (customInstructions?: string) => {
  if (customInstructions?.trim()) {
    throw new HarnessCapabilityUnsupportedError({
      harnessId: 'opencode',
      message: "Harness 'opencode' supports native manual compaction, but OpenCode does not expose custom compaction instructions through the supported API.",
    });
  }
  if (activeTurn) {
    throw new HarnessCapabilityUnsupportedError({
      harnessId: 'opencode',
      message: "Harness 'opencode' supports manual compaction between turns; compacting during an active turn is not supported by the bridge transport.",
    });
  }
  await runCompactOperation({ /* ... */ onCompaction: part => pendingCompactionParts.push(part) });
},
// :1236–1258 — the operation wires ONLY compaction/finish/error and awaits done
const unsubs = [
  channel.on('compaction', msg => onCompaction(msg)),
  channel.on('finish', () => { for (const u of unsubs) u(); pendingResolve!(); }),
  channel.on('error', msg => { for (const u of unsubs) u(); pendingReject!(msg.error); }),
];
channel.send({ type: 'start', operation: 'compact', prompt: '', tools: [], /* ... */ });
await done;
// :916–918 — the NEXT turn drains the buffer before wiring fresh listeners
while (pendingCompactionParts.length > 0) {
  forward(pendingCompactionParts.shift()!);
}
```

**Flow:** doCompact rejects custom instructions (unsupported by the API) AND an active turn (the bridge transport cannot compact mid-turn) → runCompactOperation subscribes only compaction/finish/error and sends the empty-prompt compact start → every `compaction` part routes into the session buffer instead of being emitted (there is no turn consumer to receive it) → finish/error settles the operation → the next wireTurn flushes the buffer with a shift loop BEFORE subscribing its fresh listeners, so the following turn's consumer observes the compaction that happened before it, in order, ahead of any of that turn's events.
**Invariant:** compaction parts are never lost and never reordered relative to the next turn; compaction never runs mid-turn (loud rejection, not silent deferral); custom instructions are rejected loudly rather than dropped; the buffer belongs to the SESSION, not the turn, so it survives across detach/reattach of the same process.
**Probe:** NO dedicated doCompact/pendingCompactionParts test exists in `opencode-harness.test.ts` (coverage caveat — deterministic read only). Supporting bridge-side evidence read this pass: `bridge/index.ts:777–850` (compactionSettled deferred + 250ms grace race + synthesized `{type:'compaction', trigger:'manual', missingSummary:true}` fallback) and `bridge/create-emit-stream-event.ts:279–281` (`session.next.compaction.ended` → harness `compaction` mapping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "pendingCompactionParts doCompact runCompactOperation operation compact", limit: 10 });
```

## Verdict
Adopt out-of-turn buffering + flush-at-next-wire for any dialect whose runtime compacts between turns; adapt the operation name, gate set, and buffer lifetime; omit the bridge-side settle ladder (separate subsystem, recorded queue). Cross-dialect contrast: claude-code rides `/compact [text]` on the user-message rail instead (in-turn steering, no buffering — see its test :903–919); codex and deepagents reject manual compaction outright (auto-only / unsupported). Caveat: host-side rail pinned by read only, no direct test.
