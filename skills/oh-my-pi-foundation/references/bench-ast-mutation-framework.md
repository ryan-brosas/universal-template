<!-- capsule-v2 -->
# AST source-edit mutations — byte-range edits with a dual-parser fallback and a re-parse validity gate

**Source:** oh-my-pi (MIT) `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you introduce a subtle, precision-testing bug into TypeScript source by mutating its AST and then emitting the change as byte-range source edits — while keeping every mutation syntactically valid and fully specified by before/after snippets?

## BaseAstMutation — parse → collect → mutate → source-edit, plus the composite
**Path/Symbol:** `packages/typescript-edit-benchmark/src/mutations.ts` — `BaseAstMutation` (236-275), `parseCode` (82-120), `applySourceEdits` (197-213), `snippetFromSource`/`snippetFromNode` (177-195), `mutateIdentifier` (57-66), `IdentifierMultiEditMutation` (661-905), `CompositeMultiEditMutation` (1431-1484), `OffByOneMutation` (1486-1555), `ALL_MUTATIONS`/`CATEGORY_MAP` (1574-1599).
**Signature:** `interface Mutation { name; category; multiHunk?; canApply(content): boolean; mutate(content, rng): [string, MutationInfo] }`; `MutationInfo = { lineNumber, originalSnippet, mutatedSnippet, identifier? }`.
**Data Shape:** `parseCode` tries a Flow plugin set first, then a TypeScript set (both with `errorRecovery:true`, `allowReturnOutsideFunction:true`), returning null only if both fail. `applySourceEdits` sorts edits by descending start and rejects any overlap or out-of-range edit. `mutateIdentifier` swaps the first two chars (or, for doubled first chars, rotates last→first) and returns null if the result equals the input. `CompositeMultiEditMutation` applies 3-5 random token-level mutations in sequence, requiring ≥2 to land.

### Decisive source
```ts
function applySourceEdits(content: string, edits: SourceEdit[]): string | null {
    const sorted = [...edits].sort((a, b) => b.start - a.start);   // descending
    let previousStart = content.length + 1;
    let out = content;
    for (const edit of sorted) {
        if (edit.start < 0 || edit.end < edit.start || edit.end > out.length) return null;
        if (edit.end > previousStart) return null;                  // overlap ⇒ reject
        out = `${out.slice(0, edit.start)}${edit.replacement}${out.slice(edit.end)}`;
        previousStart = edit.start;
    }
    return out;
}
```
```ts
// BaseAstMutation.mutate: mutate the chosen node, then re-serialize JUST that
// node and splice it back into the ORIGINAL source by byte range
const chosen = randomChoice(candidates, rng);
const originalRange = nodeRange(chosen.path.node);
const info = this.applyCandidate(parsed, chosen, rng);
const edits = this.buildEdits(parsed, chosen, originalRange);   // replacement = snippetFromNode(node)
const mutated = applySourceEdits(content, edits);
if (!mutated || mutated === content) return [content, noopInfo()];
```
**Flow:** `canApply` = parse + collect ≥1 candidate (cheap gate before `mutate`) → `mutate` parses (dual plugin sets), collects candidates via a Babel `traverse` visitor, picks one with the seeded rng, applies the operator/structural change to the AST node, then re-serializes ONLY that node (`snippetFromNode` via `@babel/generator`) and splices it back into the ORIGINAL source text by byte range (`applySourceEdits`) — never re-emitting the whole file, so untouched formatting is preserved. Structural mutations (`duplicate-block`, `move-distant-block`) additionally re-parse the mutated output and reject if it no longer parses. `IdentifierMultiEditMutation` walks scope bindings, picks one with ≥2-3 reference lines, mutates its identifier, and edits 2-4 distinct reference lines (dedup by start:end) so the rename is a genuine multi-hunk task.
**Invariant:** the mutation must change the source (mutated ≠ content) and every emitted `MutationInfo` snippet must actually appear in its side (verified downstream in `buildCaseEntries`). Byte-range splicing preserves all untouched formatting; the dual-parser fallback means Flow-typed fixtures still parse. Structural mutations that would produce a parse error are rejected, never shipped.

**Probe:** `packages/typescript-edit-benchmark/test/hunks.test.ts` exercises the shared hunk machinery; the mutation set itself is exercised end-to-end by `generate.ts`'s re-solve gate (`buildPrompt` → `solveRenderedHunks` must reproduce the expected file, else the case is rejected) — see `bench-unique-hunk-rendering`. The 23-mutation taxonomy (`ALL_MUTATIONS`, 10 categories) is the calibration target behind `MUTATION_PLANS` in `generate.ts:157-181`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "BaseAstMutation applySourceEdits IdentifierMultiEditMutation CompositeMultiEditMutation ALL_MUTATIONS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mutation framework for any precision-edit benchmark generator: AST-collect → mutate node → re-serialize single node → byte-range splice into original source → re-parse gate for structural ops. Adapt the plugin sets and visitor set to your language; omit OMP-specific mutation taxonomy. The byte-range-splice-preserves-formatting + re-parse-validity-gate invariants are what a porter gets wrong.
