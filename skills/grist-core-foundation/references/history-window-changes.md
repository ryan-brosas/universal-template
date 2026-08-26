<!-- capsule-v2 -->
# History window change assembly — how do you compute "what changed between two versions" from append-only action history?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Given state hashes and an actions ledger, how do you fold N stored actions into ONE summary with row caps, and which direction constraint makes it valid?

## HashUtil offsets slice the states array; stored actions fetched by number, REVERSED, summarized, then concatenated left-to-right
**Path/Symbol:** `app/server/lib/DocApi.ts:getChanges` (:2388–2433); helpers `HashUtil.hashToOffset` (HashUtil.ts), `summarizeAction`/`concatenateSummaries` (`app/common/ActionSummarizer.ts`); consumers: GET `/compare` (:1111–1132), `_compareDoc` cross-doc (:2192–2254), POST `/propose` (:1138–1164).
**Signature:** `getChanges(docSession, activeDoc, options: {states: DocState[]; leftHash: string; rightHash: string; maxRows?: number|null}): Promise<DocStateComparison>`.
**Data Shape:** `states` = newest-first list of `{n: actionNum, h: hash}`; result `DocStateComparison = {left, right, parent, summary, details: {leftChanges: empty, rightChanges: ActionSummary}}`. `maxRows` feeds `maximumInlineRows` (truncation marker `mayBeIncomplete` — see action-summary-diff capsule).

### Decisive source
```ts
if (!await activeDoc.canCopyEverything(docSession)) { throw new ApiError("insufficient access", 403); }
const finder = new HashUtil(states);
const leftOffset = finder.hashToOffset(leftHash);
const rightOffset = finder.hashToOffset(rightHash);
if (rightOffset > leftOffset) {
    throw new Error("Comparisons currently require left to be an ancestor of right");
}
const actionNums: number[] = states.slice(rightOffset, leftOffset).map(state => state.n);
const actions = (await activeDoc.getActions(actionNums)).reverse();
let totalAction = createEmptyActionSummary();
for (const action of actions) {
    if (!action) { continue; }
    const summary = summarizeAction(action, { maximumInlineRows: maxRows });
    totalAction = concatenateSummaries([totalAction, summary]);
}
// parent: states[leftOffset]; summary: left===right offset ? "same" : "right"
// details.leftChanges is ALWAYS {tableRenames:[], tableDeltas:{}} — right-only by construction
```
**Flow:** broad-read gate (change computation ignores granular access rules — hence canCopyEverything, 403 otherwise) → hashes→offsets via HashUtil (accepts HEAD, numeric-prefix, `~N` ancestors; rejects lowercase/malformed) → ancestor check (rightOffset ≤ leftOffset since states are newest-first) → fetch the window's stored actions by number → `.reverse()` restores chronological order → summarize each with inline-row cap → concatenate into one net summary. Cross-doc compare reuses this endpoint recursively over internal forwarding, computing each side's changes from the common parent separately.
**Invariant:** left-must-be-ancestor keeps folding semantically valid (net diff = replay of the window); violating it throws rather than approximating. Empty summaries for pruned/null actions are skipped, NOT errors — history truncation degrades gracefully into a partial window. `leftChanges` is structurally empty because the API computes forward diffs only.
**Probe:** `test/server/lib/HashUtil.ts:6–26` (HEAD=0, case-sensitive reject, `3123~N` ancestor ladder) + DocApiSql/compare coverage caveat: the fold loop itself is exercised indirectly via compare endpoints; direct unit pins live on HashUtil.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "getChanges HashUtil hashToOffset concatenateSummaries getActions", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt the offset-slice + reverse-fold recipe for version diffs over append-only ledgers (audit logs, migration histories). Adapt summarization granularity freely; keep the ancestor precondition loud. Omit cross-doc forwarding unless you have multi-worker doc placement.
