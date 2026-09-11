<!-- capsule-v2 -->
# Edit snapshot budget — how do you carry full pre/post file snapshots in tool results without ballooning the session log?

**Source:** Oh My Pi MIT `main@96f42809764f0907f7d6b115eab5710de28941de`; Codebase Memory `oh-my-pi`. **Question:** When edit-tool `details` hold whole `oldText`/`newText` for diff UIs, how do you stop large edits from bloating persisted sessions without breaking clients that need the diff?

## Shared-budget pruning with a suppress-downstream-partial-diff marker
**Path/Symbol:** `packages/coding-agent/src/edit/snapshot-details.ts` — `pruneOversizedEditSnapshots` (67–77), `pruneSnapshot` (31–37), `capPerFileSnapshots` (46–59), `MAX_EDIT_SNAPSHOT_TEXT_CHARS = 32_768` (27); wrapped around EVERY edit-tool payload by `packages/coding-agent/src/edit/hashline/execute.ts:renderSection` (127–212).
**Signature:** `function pruneOversizedEditSnapshots(details: EditToolDetails | EditToolPerFileResult): EditToolDetails | EditToolPerFileResult` (per-file overload declared first so the more specific shape wins resolution).
**Data Shape:** payloads carry optional `oldText?`, `newText?`, `snapshotsPruned?: boolean`; batch payloads add `perFileResults[]`. Budget is COMBINED `oldText.length + newText.length ≤ 32_768` chars, applied per entry AND as one running aggregate across the batch.

### Decisive source
```ts
function pruneSnapshot<T extends WithSnapshot>(details: T): T {
    if ((details.oldText?.length ?? 0) + (details.newText?.length ?? 0) <= MAX_EDIT_SNAPSHOT_TEXT_CHARS)
        return details;
    const { oldText: _old, newText: _new, ...rest } = details;
    return { ...rest, snapshotsPruned: true } as T;   // strip AND mark
}
// Shared budget across the batch, in order: early entries keep their diff
// visualization; later entries degrade to text-only once bytes run out.
let remaining = MAX_EDIT_SNAPSHOT_TEXT_CHARS;
const kept = (perEntry.oldText?.length ?? 0) + (perEntry.newText?.length ?? 0);
if (kept <= remaining) { remaining -= kept; return perEntry; }
```

**Flow:** every edit-tool result construction wraps its `details`/per-file entries in `pruneOversizedEditSnapshots` → per-entry cap first → then the ordered aggregate walk strips any entry whose kept chars exceed the remaining shared budget → consumers (ACP event mapper) treat `snapshotsPruned: true` as "no raw snapshots ⇒ no diff ToolCallContent", while plain text content still flows.
**Invariant:** pruning is free for the LLM — provider serializers send only `content`, never `details`, so stripped snapshots never paid for context anyway (the #3786 300 KB-per-turn bloat was pure session JSONL); the `snapshotsPruned` marker must propagate to AGGREGATE payloads too — otherwise a pruned big-shrink entry followed by a small kept entry lets the aggregator present the small `oldText` as a whole-file pre-image and clients render a misleading partial diff (#3787); degradation is graceful and ordered, never all-or-nothing.
**Probe:** `packages/coding-agent/test/edit-snapshot-details.test.ts:61` (unit describe over the pruner), `:181` ("pruned first-entry snapshots suppress aggregate snapshots from a later kept entry" — the #3787 marker RED/GREEN), `:224` ("strips per-file snapshots once the shared budget is spent" — five ~10 KB sections bust the 32 KB shared budget through real `executeHashlineSingle`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^pruneOversizedEditSnapshots$", limit: 5 });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.coding-agent.src.edit.snapshot-details.pruneOversizedEditSnapshots" });
```

## Verdict
Adopt the combined-char budget, per-entry-then-shared-aggregate ordering, strip-and-mark (`snapshotsPruned`) semantics, and the rule that a marked entry suppresses aggregate diff rendering downstream; adapt the 32 KB constant and payload field names to your host; omit nothing — the module has zero host dependencies beyond type imports. Companion (separate concern): multi-section edits narrow deferred-LSP flush to the LAST section via `execute.ts:narrowBatchRequest` (96–98, `{ id, flush: isLast && outer.flush }`) so diagnostics arrive once per batch, not per section.
