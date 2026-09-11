<!-- capsule-v2 -->
# Small-edit fan-out — how does a single accepted edit feed BOTH the immediate prompt context and the durable history, and which guard decides each?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What is the exact split between the synchronous diff injection (context) and the fire-and-forget history write, and why do they use different contextLines?

## Two consumers, one security gate
**Path/Symbol:** `core/nextEdit/context/processSmallEdit.ts:processSmallEdit` (whole, 53L).
**Signature:** `processSmallEdit(beforeAfterdiff: BeforeAfterDiff, cursorPosBeforeEdit, cursorPosAfterPrevEdit, configHandler, getDefsFromLspFunction, ide): Promise<void>`.
**Data Shape:** pulls `latestContextData` off the `EditAggregator` singleton (cast through `any`) with a DEFAULTS FALLBACK `{configHandler, getDefsFromLspFunction, recentlyEditedRanges: [], recentlyVisitedRanges: []}`.

### Decisive source
```ts
const currentData = (EditAggregator.getInstance() as any).latestContextData || { /* defaults */ };

if (!isSecurityConcern(beforeAfterdiff.filePath)) {
  NextEditProvider.getInstance().addDiffToContext(
    createDiff({
      beforeContent: beforeAfterdiff.beforeContent,
      afterContent:  beforeAfterdiff.afterContent,
      filePath:      beforeAfterdiff.filePath,
      diffType:      DiffFormatType.Unified,
      contextLines: 3, // NOTE: This can change depending on experiments!
    }),
  );
}

void processNextEditData({ ...beforeAfterdiff, cursorPosBeforeEdit, cursorPosAfterPrevEdit,
                           ...currentData });   // NOT awaited — history write never blocks the editor
```

**Flow:** read the aggregator's captured per-request context bundle → SECURITY GATE → inject a tight 3-context-line unified diff into `NextEditProvider`'s live prompt context SYNCHRONOUSLY → separately fire-and-forget (`void`) `processNextEditData`, which re-renders with 25-line diffs for the durable prev-edit ledger + telemetry.
**Invariant:** The security gate protects only the PROMPT-INJECTION path — the telemetry/history path runs regardless of file sensitivity in this function (the ledger's forget-ladder lives in processNextEditData). The two contextLines values are deliberate: 3 lines = what the next prompt can afford; 25 lines = what future trimming might need. Losing `await` on the history path is intentional (editor latency wins); porters who await it add latency to every keystroke commit.
**Probe:** deterministic source pins: `grep -n 'contextLines: 3\|contextLines: 25\|void processNextEditData\|isSecurityConcern' core/nextEdit/context/processSmallEdit.ts core/nextEdit/context/processNextEditData.ts`. Coverage caveat: no direct vitest suite at this pin; consumer chain pinned by source.
**Note (type-safety residue):** `(EditAggregator.getInstance() as any).latestContextData` reaches past the class surface — porters should expose a typed accessor instead of copying the cast.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "processSmallEdit addDiffToContext processNextEditData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sync-prompt/fire-and-forget-history split with its dual contextLines rationale and the prompt-only security gate placement; adapt gate scope if your threat model requires gating telemetry too; omit the aggregator-cast plumbing in favor of typed accessors.
