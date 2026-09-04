<!-- capsule-v2 -->
# NextEdit chain state machine — singleton chain id + previousCompletions + deleteChain history re-push

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How is a multi-step "chain" of accepted edits tracked so step N+1 knows about step N, and what must happen to that state when a chain is torn down?

## Key facts
**Path/Symbol:** `core/nextEdit/NextEditProvider.ts` — private state fields (:68-76), `chainExists`/`getChainLength`/`getPreviousCompletion` (:210-220), `deleteChain` (:222-243), `startChain`/`getChain`/`isStartOfChain` (:245-255), `_handleCompletion` outcome push (:530-536).
**Signature:** `deleteChain(): Promise<void>`, `startChain(id?: string)`, `getPreviousCompletion(): NextEditOutcome | null` (index `[0]`, NOT last), `provideInlineCompletionItemsWithChain(ctx, nextEditLocation, token, usingFullFileDiff)` (:557-599) → wraps `buildAutocompleteInputFromChain` (:601-627) which builds `{pos: regionStart, filepath: previousOutcome.fileUri, ...ctx}`.
**Data Shape:** chain state = `currentEditChainId: string | null` + `previousCompletions: NextEditOutcome[]`; `isStartOfChain()` is `length === 1`. The chain is NOT in PrefetchQueue despite its docstring — the queue holds only warmed diff-group outcomes.

### Decisive source
```ts
// :222-243 — teardown is not just "clear arrays": the file's CURRENT content
// must be pushed into DocumentHistoryTracker or the next prompt's historyDiff
// would be computed against a stale pre-chain snapshot.
public async deleteChain(): Promise<void> {
    PrefetchQueue.getInstance().abort();
    this.currentEditChainId = null;
    this.previousCompletions = [];
    if (this.previousRequest) {
      const fileContent = (await this.ide.readFile(this.previousRequest.filepath)).toString();
      const ast = await getAst(this.previousRequest.filepath, fileContent);
      if (ast) {
        DocumentHistoryTracker.getInstance().push(
          localPathOrUriToPath(this.previousRequest.filepath), fileContent, ast);
      }
    }
}
```
```ts
// :555-559 on provideInlineCompletionItemsWithChain — upstream's own words:
// "This is invoked when we call the model in the background using prefetch.
// It's not currently used anywhere (references are not used either), but I
// decided to keep it in case we actually need to use prefetch."
```

**Flow:** `startChain()` mints a uuid chain id → each `provideInlineCompletionItems` run pushes its outcome into `previousCompletions` after postprocessing (:532) and JetBrains auto-marks it displayed (`_markDisplayedIfJetBrains` :541-549, ideType check) → `getPreviousCompletion()[0]` feeds `provideInlineCompletionItemsWithChain` for background continuation → teardown goes through `deleteChain` which aborts prefetch FIRST, then clears both state fields, then re-syncs DocumentHistoryTracker from live disk content (guarded on AST availability).

**Invariant:** `previousCompletions[0]` is read as "the previous completion" while new outcomes are `push()`ed — the array is consumed front-first; a porter who reads `[length-1]` chains onto the WRONG edit. Chain teardown without the DocumentHistoryTracker re-push silently corrupts every subsequent `historyDiff` prompt. The with-chain entry point is dormant-by-choice (upstream comment), not dead by accident.

**Probe:** `grep -c 'this.previousCompletions' core/nextEdit/NextEditProvider.ts` → 6 (:215 length, :219 front-read, :226 teardown clear, :250 getChain, :254 start-of-chain, :532 outcome push); `grep -c 'PrefetchQueue.getInstance().abort()' core/nextEdit/NextEditProvider.ts` → 1; `grep -c 'not currently used anywhere' core/nextEdit/NextEditProvider.ts` → 1.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "NextEditProvider startChain deleteChain previousCompletions", limit: 8 })`

## Verdict
Adopt the two-field chain state + front-index consumption rule and the abort→clear→re-push teardown order. Omit the dormant with-chain prefetch wrapper until a host actually wires background chaining.
