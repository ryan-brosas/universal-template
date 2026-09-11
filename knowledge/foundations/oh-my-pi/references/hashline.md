<!-- capsule-v2 -->
# Hashline apply pipeline — pure materialize, syntax as the only judge

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you turn line-anchored edits into a sound file mutation without letting a repair pass second-guess the author?

## One pure pass materializes; syntax is the only judge
**Path/Symbol:** `packages/hashline/src/apply.ts:applyEdits` (1315–1390) → `materializeEdits` (1223); helpers `repairAfterInsertLandings` (1087), `normalizeTextualBoundaryEchoes` (386), `dropTrailingPhantomDeletes`, `validateLineBounds`.
**Signature:** `applyEdits(text: string, edits: readonly Edit[], options?: ApplyEditsOptions): ApplyResult` where `ApplyResult { text, firstChangedLine?, warnings? }`.
**Data Shape:** LF-split lines; edits pre-resolved of clipboard/block kinds then cloned with sequential indices; `baselineParses` / `authoredParses` booleans gate every speculative path.

### Decisive source
```ts
const authoredResult = materializeEdits(fileLines, normalized.edits);
const baselineParses = parsesCleanly(options.path, text);
const authoredParses = parsesCleanly(options.path, authoredResult.text);
// Exact-text normalization is evidence-complete. If it leaves a parsing
// result, no speculative keep/drop variant may second-guess it.
if (authoredParses) {
  if (ambiguity) throw new Error(ambiguousBoundaryEchoMessage(...));
  return finish(authoredResult, leading);
}
const repaired = repairBoundaryVariants(normalized.edits, fileLines, options.path, baselineParses);
```

**Flow:** clipboard pre-pass (`resolveClipboardEdits`) captures cuts from the original lines and expands pastes in authored order → arriving block/cut/paste at this point are internal-wiring bugs and throw → drop trailing phantom deletes, validate bounds, repair replacement indentation, land inserts, normalize boundary echoes (indentation + textual), collecting warnings with order preserved → bottom-up materialization keeps earlier indices valid and tracks 1-indexed `firstChangedLine` → authored result wins UNLESS it stopped parsing while the baseline parsed; only then do tree-sitter-validated boundary variants run, accepted only if they parse. On ambiguity the applier never silently keep/drops — it throws `ambiguousBoundaryEchoMessage`; when nothing is proven it returns the edit exactly as written plus a post-apply advisory (`editBrokeParseWarning`) naming that THIS patch demonstrably introduced the parse error.

**Invariant:** the applier is a pure splice over `\n`-split lines — no I/O; a mis-set replacement boundary is repaired only when the replacement parses; warnings are never dropped on any return path.

**Probe:** `packages/hashline/test/core-contracts.test.ts` (input splitter, cut/blank payload semantics, patcher preflight, recovery), `patcher.test.ts` snapshot tag integrity + tag-based path recovery — both green at `96f428097`.

## Deferred block edits resolve against real syntax
**Path/Symbol:** `packages/hashline/src/block.ts:resolveBlockEdits` (105–275).
**Signature:** `resolveBlockEdits(edits, text, path, resolver?: BlockResolver, options?): readonly Edit[]` — resolver receives `{ path, text, line }`, returns `BlockSpan | null`.
**Data Shape:** non-block edits pass untouched; unresolved-block policy is `options.onUnresolved ?? "throw"`; synthesized inserts/deletes get sequential `index` purely for readability (the applier re-derives indices from array order).

### Decisive source
```ts
if (span === null) {
  // `insert_after_block N:` never fails the patch — lower it to plain
  // `insert after N:` with a warning instead. Two flavors:
  // - anchored on a pure closing-delimiter line: no block begins
  //   there, but line N IS the end of one, and "after the end of the
  //   block" is exactly the plain form — warn with the opener rule.
  // - otherwise (unsupported language, blank line, unparsable block,
  //   or no resolver wired): "after the block at N" degrades to
  //   "after line N" — warn to verify the landing line.
```

**Flow:** resolver returns start/end for the anchor line; a single-line span means line N is a bare statement, not an opener — the common mis-anchor that lands a body in the wrong scope (e.g. between a case body and its `break;`) — rejected with a message pointing at the line, dropped only on the lenient preview path. `insert_after_block`/`paste_after_block` on an unresolvable anchor lowers to plain after-N with a warning (closer-line flavor explains the opener rule); other modes throw `BLOCK_UNRESOLVED` with a suggestion scan (next block within ~64 lines / enclosing block).

**Invariant:** block ops must be fully concrete before the applier; a failed block anchor degrades to a warned plain anchor or a loud error — never a silent wrong-scope insert.

**Probe:** `packages/hashline/test/block.test.ts` + `patcher.test.ts` cover replacement-boundary and block-anchor edge cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(applyEdits|materializeEdits|repairAfterInsertLandings|normalizeTextualBoundaryEchoes|repairBoundaryVariants|resolveBlockEdits|parsesCleanly)$", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.apply.applyEdits" });
```

## Verdict
Adopt pure materialization with baseline-vs-authored parse gating, repair-only-on-parse-failure, loud ambiguity errors, and the insert_after lowering ladder; adapt the syntax oracle (tree-sitter → host parser) and warning taxonomy; omit the native bridge specifics unless porting the whole package. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk files.
