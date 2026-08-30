<!-- capsule-v2 -->
# Claude-code bridge compaction latch — how do you merge a two-part, unordered runtime notification into one well-formed event?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the runtime reports one semantic event (context compaction) through two independent channels whose arrival order is not guaranteed, how does the in-sandbox bridge emit exactly one merged event per compaction?

## Two-half latch with reset-on-emit
**Path/Symbol:** `packages/harness-claude-code/src/bridge/compaction-latch.ts` — `createCompactionLatch` (:29–62), `tryEmit` (:35–51); wiring in `packages/harness-claude-code/src/bridge/index.ts` — latch creation (:309–312), `PostCompact` hook (:363–378), boundary callback into the stream translator (:414); boundary extraction in `packages/harness-claude-code/src/bridge/create-emit-stream-event.ts` (:174–187).
**Signature:** `createCompactionLatch(emit: (event: CompactionEvent) => void): { onBoundary(boundary): void; onSummary(summary: string): void }`.
**Data Shape:** half A = `{trigger: 'manual'|'auto', tokensBefore?, tokensAfter?}` from the `compact_boundary` system message's `compact_metadata` (`pre_tokens`/`post_tokens`, included only when numeric); half B = the summary string from the `PostCompact` hook's `compact_summary` (latched only when a string); merged event = `{type:'compaction', trigger, summary, tokensBefore?, tokensAfter?}` with token fields omitted entirely when absent.

### Decisive source
```ts
// compaction-latch.ts:35–51 — emit ONLY when both halves exist, then reset so
// a second compaction in the same turn emits again
const tryEmit = (): void => {
  if (!boundary || summary === undefined) return;
  emit({
    type: 'compaction',
    trigger: boundary.trigger,
    summary,
    ...(boundary.tokensBefore !== undefined ? { tokensBefore: boundary.tokensBefore } : {}),
    ...(boundary.tokensAfter !== undefined ? { tokensAfter: boundary.tokensAfter } : {}),
  });
  boundary = undefined;
  summary = undefined;
};
// index.ts:363–378 — the hook half returns {} so compaction proceeds
hooks: {
  PostCompact: [{
    hooks: [async (input: { compact_summary?: unknown }) => {
      if (typeof input?.compact_summary === 'string') {
        compaction.onSummary(input.compact_summary);
      }
      return {};
    }],
  }],
},
```

**Flow:** the SDK message loop feeds the stream translator; a `system`/`compact_boundary` message extracts trigger + token counts and calls `onBoundary` (the translator then RETURNS — the boundary itself produces no other parts) → separately, the SDK fires the `PostCompact` hook after compaction, whose handler latches `compact_summary` via `onSummary` and returns empty output so compaction is not blocked → whichever half arrives second triggers `tryEmit`, which publishes the single merged `compaction` event on the bridge stream and resets both slots for the next compaction in the same turn.
**Invariant:** consumers see EXACTLY ONE `compaction` event per compaction regardless of channel order, and never a half-formed one (no summary-less or boundary-less emission); the latch is per-turn (created inside runTurn) so state cannot leak across turns; the hook must return empty output or it would alter/block the compaction itself.
**Probe:** `packages/harness-claude-code/src/bridge/compaction-latch.test.ts` (86L, 5 cases): boundary-first merge with token fields; summary-first merge; token-field omission when the boundary reported none; reset-after-emit (two compactions in one turn ⇒ two events with distinct payloads); lone-half non-emission plus orphan-summary pairing with the NEXT boundary.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createCompactionLatch compact_boundary PostCompact onCompactionBoundary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-slot latch + reset-on-emit shape for any runtime that splits one semantic event across unordered channels (message stream vs hook/callback); adopt the type-guarded half acceptance (string-only summary, numeric-only token counts) and field-omission-over-null output style; adapt the two observation points to your runtime's channels; omit the latch where the runtime already delivers a single atomic compaction record. Bridge-side twin of the host-side /compact rail documented in the pass-23 dialect-adapter plane (the host adapter sends the slash command over the user-message rail; see also harness-opencode-compaction-rail.md for the native-operation variant): this latch merges what the runtime reports back. Caveat: the wiring sites (index.ts :309–312/:363–378/:414, translator :174–187) are deterministic-read-only — the latch kernel itself is fully test-pinned.
