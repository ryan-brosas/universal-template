<!-- capsule-v2 -->
# Guided-mode patch synthesis — generating the exact edit-tool call that turns actual into expected

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** In "guided" benchmark mode, how do you synthesize a copy-pasteable patch — in the model's own edit language — that transforms the current fixture into the expected one, and when should guidance be withheld?

## Diff→ops compiler with BOF/EOF anchors and complexity guards
**Path/Symbol:** `packages/metaharness/adapters/edit/runner.ts` — `buildGuidedHashlinePatch` (606-681), `buildGuidedContext` (683-723), mutation-intent check `evaluateMutationIntent` (532-599), no-change hint `appendNoChangeMutationHint`+`buildMutationPreviewAgainstOriginal` (363-423).
**Signature:** `function buildGuidedHashlinePatch(file: string, actual: string, expected: string): string | null`; `buildGuidedContext(task, cwd, expectedDir, config): Promise<string | null>`.
**Data Shape:** output = hashline header (`¶path#tag`, tag from an in-memory snapshot of the normalized actual) + ops: pure inserts as `BOF↓`/`EOF↓`/`N↑` (insert ABOVE line N), replacements as `start-end:` (or single `N!` delete), payload indented under the op. Guards: ≤25 ops, ≤20k chars.

### Decisive source
```ts
// File-trailing newline produces a phantom empty last entry that is not a
// real line; the hashline grammar's line numbers count real lines only.
const fileLineCount =
    actualLines.length > 0 && actualLines[actualLines.length - 1] === ""
        ? actualLines.length - 1
        : actualLines.length;
...
if (pendingRemoved === 0) {
    if (pendingStart <= 1)               ops.push(`BOF↓${formatPayload(pendingAdded)}`);
    else if (pendingStart > fileLineCount) ops.push(`EOF↓${formatPayload(pendingAdded)}`);
    else                                   ops.push(`${pendingStart}↑${formatPayload(pendingAdded)}`);
} else {
    const anchor = startLine === endLine ? `${startLine}` : `${startLine}-${endLine}`;
    ops.push(pendingAdded.length === 0 ? `${anchor}!` : `${anchor}:${formatPayload(pendingAdded)}`);
}
```

**Flow:** walk the line diff of actual→expected accumulating contiguous removed/added hunks → flush each hunk into the edit language's ops using PRE-EDIT line numbers (pure insert at top ⇒ BOF, past EOF ⇒ EOF, otherwise insert-above so content LANDS on the target line; deletes/replaces carry their range) → record a snapshot tag of the CRLF-normalized actual and prepend the header → refuse to guide when the diff exceeds the complexity guard or isn't expressible as straight insert/replace/delete → embed the resulting tool-call args JSON in the task prompt ("copy/paste args exactly"). Companions: after verification failure the retry context includes the expected-vs-actual diff plus a mutation-intent verdict (target-line match / original-present-and-mutation-gone); on "No changes made" errors the error text is augmented with a `-line:text` preview of how the file ALREADY differs from the original fixture.
**Invariant:** all line numbers refer to the pre-edit file (the applier renumbers); the trailing-newline phantom line must be excluded from counts or every EOF op lands one line late; guidance is bounded — an over-complex patch would teach the model nothing and blow context, so withholding it is correct behavior; snapshot tags come from the file's real current bytes, never assumptions.
**Probe:** no direct unit test drives guided synthesis (needs fixture dirs + diff fixtures) — coverage caveat. Adjacent deterministic pieces ARE pinned by report tests: `renders atom input args directly in edit error patch blocks` and the category table (`adapters/edit/runner.test.ts:110-180`) cover the failure-report half this seam feeds.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "buildGuidedHashlinePatch buildGuidedContext evaluateMutationIntent appendNoChangeMutationHint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the idea for any self-improving eval loop: compile the ground-truth answer into the agent's native action format, bound its size, embed it verbatim, and enrich failures with already-differs previews. Adapt the op grammar to your own edit tool (this instance targets OMP hashline); omit the specific regexes. Recorded honestly: synthesis flow is source-grounded; its report-side outputs are test-pinned.
