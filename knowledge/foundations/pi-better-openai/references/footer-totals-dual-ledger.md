<!-- capsule-v2 -->
# Footer totals dual ledger — how do you track session-cumulative token/cost spend when the host can only hand you either the whole history or one completed turn?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How do you keep a running usage total O(1) per turn while staying correct across compaction and tree edits that make incremental deltas wrong?

## Full-rescan vs incremental-delta ledger
**Path/Symbol:** `index.ts:footerTotals` slot (:181), `refreshFooterTotals` (:239-249), incremental branch inside the `turn_end` handler (:1264-1275), rescan triggers in `session_start` (:1236) / `session_compact` (:1277-1283) / `session_tree` (:1285-1291).
**Signature:** `function refreshFooterTotals(ctx): void`; ledger shape `{ input: number, output: number, cacheRead: number, cacheWrite: number, cost: number }`.
**Data Shape:** Ledger accumulates ONLY assistant-message usage. Two write paths into the SAME object: full rescan (iterate `ctx.sessionManager.getEntries()`, filter `type==="message" && role==="assistant"`, sum all five fields) and single-turn delta (add ONE assistant message's usage fields).

### Decisive source
```ts
// turn_end: fast path for the common case, rescan as fallback
pi.on("turn_end", (event, ctx) => {
  invalidateContextUsage();
  if (event.message?.role === "assistant") {
    footerTotals.input += event.message.usage.input;    // delta += this turn only
    ...
    footerTotals.cost += event.message.usage.cost.total;
  } else refreshFooterTotals(ctx);                      // non-assistant turn → rebuild from scratch
  updateFooter(ctx);
});

// structure changed → history is no longer a prefix of what we summed
pi.on("session_compact", (_e, ctx) => { invalidateContextUsage(); refreshFooterTotals(ctx); ... });
```

**Flow:** session start / compact / tree-edit → FULL rescan (history may have been rewritten; a delta would double-count or miss); normal completed turn with an assistant message → O(1) delta add; anything else at turn end (tool-only or user-role turn payload) → conservative full rescan; every path ends in `updateFooter(ctx)` so the rendered line never lags the ledger.

**Invariant:** The incremental fast path is valid ONLY while history is append-only — the moment the host rewrites it (compaction, tree switch/checkout), the delta ledger is meaningless and MUST be rebuilt by rescan. Porters get this wrong by treating `turn_end` deltas as universally correct, or by rescanning every render (O(session) per frame). The five fields are summed together everywhere — never mix a rescan's snapshot with outstanding deltas of different field sets.

**Probe:** `tests/footer.test.ts:255` "adds completed-turn usage without rescanning the full session" — after `session_start`, emitting `turn_end` with `{input:1200, output:300, cacheRead:400, cacheWrite:50, cost:{total:0.25}}` renders exactly `↑1.2k ↓300 R400 W50 $0.250` and `getEntries` was called exactly ONCE (the initial scan), proving the delta path skipped the rescan. Coverage caveat: compaction/tree rescan branches are source-pinned only (`index.ts:1277-1291`) — no direct test asserts them.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "refreshFooterTotals persist writeSetting refresh cachedConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-ledger pattern (append-only window → delta; rewrite window → rescan) for any cumulative stat over a mutable transcript. Adapt the entry filter and usage field names to your host. Omit the specific five-field footer rendering.
