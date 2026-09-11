<!-- capsule-v2 -->
# Uniqueness-provable edit hunks — render prompt blocks that admit exactly one byte-exact answer

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you turn an input→expected diff into prompt-visible before/after blocks that are guaranteed unique in the input, so a model's patch is unambiguous and re-solvable to exactly one byte-exact answer?

## renderHunks + solveRenderedHunks — the re-solve proof
**Path/Symbol:** `packages/typescript-edit-benchmark/src/hunks.ts` — `placementsFromDiff` (80-112), `mergeNearbyPlacements` (119-133), `renderHunks` (144-213), `solveRenderedHunks` (220-241), `findBlockOccurrences` (33-45), `applyPlacements` (47-56), `pickFence` (259-264), `LANGUAGE_BY_EXTENSION` (243-256).
**Signature:** `placementsFromDiff(inputText, expectedText): Placement[]`; `renderHunks(inputLines, placements): RenderedHunk[] | null`; `solveRenderedHunks(inputLines, hunks): string[] | null`; `RenderedHunk = { oldBlock: string[], newBlock: string[], startLine: number, unique: boolean }`; `Placement = { start, oldLen, newLines }`.
**Data Shape:** adjacent removed/added diff runs merge into ONE placement (so a moved statement is a single replace, not delete+reinsert). `startLine` is 1-based. `unique=true` means `oldBlock` occurs exactly once in the input; `unique=false` means the prompt must state `startLine` (the block could not be disambiguated within `MAX_UNIQUENESS_EXTENSION=10` context lines).

### Decisive source
```ts
// renderHunks: trim to changed core, then extend with context until unique
const prefix = commonPrefixLength(old, fresh);
const suffix = commonSuffixLength(old, fresh, Math.min(old.length, fresh.length) - prefix);
let oldBlock = old.slice(prefix, old.length - suffix);
let newBlock = fresh.slice(prefix, fresh.length - suffix);
if (oldBlock.length === 0 && newBlock.length === 0) continue;
// pure insertion/deletion: anchor on a visible (non-blank) context line
if (oldBlock.length === 0 || newBlock.length === 0) { /* takeAbove()/takeBelow() or return null */ }
let unique = true;
for (let ext = 0; findBlockOccurrences(inputLines, oldBlock).length > 1; ext++) {
    if (ext >= MAX_UNIQUENESS_EXTENSION || !takeAbove()) { unique = false; break; }
}
// pad blank fence edges with visible context (bounded, best-effort)
```
```ts
// solveRenderedHunks: re-locate each block and re-apply; proves one answer
for (const hunk of hunks) {
    const occ = findBlockOccurrences(inputLines, hunk.oldBlock);
    const start = hunk.unique ? (occ.length === 1 ? occ[0] : /* null */)
                              : (occ.includes(hunk.startLine - 1) ? hunk.startLine - 1 : /* null */);
    placements.push({ start, oldLen: hunk.oldBlock.length, newLines: hunk.newBlock });
}
// sort by start; reject any overlap; applyPlacements
```
**Flow:** `placementsFromDiff` walks the jsdiff change list tracking the input line cursor, merging contiguous removed/added runs into one placement → `mergeNearbyPlacements(…, 2)` bridges placements separated by ≤2 context lines (a moved statement renders as one natural replace, not a delete + re-insert ending on invisible blanks) → `renderHunks` trims each placement to its changed core (common prefix/suffix), anchors pure insert/delete on a non-blank context line (blocks never start/end on a blank at a fence edge — invisible), then extends upward with context until the old block is unique or the budget is exhausted (non-unique ⇒ prompt must state `startLine`) → `solveRenderedHunks` re-locates every block (unique ⇒ exactly one occurrence; else the stated start line must actually match) and re-applies, returning null on any ambiguity/overlap — the caller uses this to guarantee the prompt admits exactly one byte-exact answer.
**Invariant:** a hunk is only `unique` when its `oldBlock` occurs exactly once in the input; a non-unique hunk is only solvable when its `startLine` points at a real occurrence. `solveRenderedHunks` is the proof oracle — if it cannot reproduce the expected file, the prompt is rejected. `pickFence` upgrades ` ``` ` to ` ```` ` when any block embeds a triple backtick.

**Probe:** `packages/typescript-edit-benchmark/test/hunks.test.ts` — `:50-59` pins that a repeated `\tstop();` block is extended with `if (y) {` context until unique; `:61-76` pins the non-unique path (four identical `value += 1;` lines ⇒ `unique=false`, `startLine` lands on a real occurrence, and `solveRenderedHunks` still reproduces the expected file); `:79-95` pins placement merging (two adjacent swapped statements render as ONE hunk; distant changes stay separate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "renderHunks solveRenderedHunks placementsFromDiff mergeNearbyPlacements pickFence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any benchmark/fixture generator that must emit unambiguous edit prompts: placements-from-diff → merge-nearby → render-unique-hunks → re-solve-as-proof. Adapt the diff engine (jsdiff here) and the uniqueness budget; omit OMP-specific line-number conventions. The re-solve-as-gate (reject any prompt the solver can't reproduce) is the core invariant — test-pinned.
