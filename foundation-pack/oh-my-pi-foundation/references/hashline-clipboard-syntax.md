<!-- capsule-v2 -->
# Hashline clipboard registers + tree-sitter syntax proof

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/hashline/src/clipboard.ts`, `syntax.ts`. **Question:** How do cut/paste edits stay deterministic across a patch batch, and when may a parser's verdict veto (or never veto) an edit?

## Clipboard resolution: capture before delete, expand before apply
**Path/Symbol:** `clipboard.ts:hasClipboardEdit` (30), `resolveClipboardEdits` (114–186), `startClipboardBatch` (189), `commitClipboard` (205), `validateClipboardSequence` (217).
**Signature:** `resolveClipboardEdits(edits, fileLines, clipboard, options?): readonly Edit[]`; `ResolveClipboardEditsOptions { onEmptyPaste?: "throw" | "drop"; onWarning? }`.
**Data Shape:** `Clipboard` carries batch-local anonymous `lines` + `pendingAnonCuts`, plus optional named registers (`named: Map<string, string[]>`); cuts carry a source range and optional register; pastes target a `gap` or a `span`.

### Decisive source
```ts
if (!hasClipboardEdit(edits)) return edits;
const onEmptyPaste = options.onEmptyPaste ?? "throw";
for (const edit of edits) {
  if (edit.kind === "cut") { writeRegister(edit, fileLines, clipboard); continue; }
  if (edit.kind === "paste") {
    const lines = readRegister(edit.register, edit.at.kind, clipboard, edit.lineNum, onEmptyPaste, options.onWarning);
    if (lines === null) continue;
    // a gap expands to synthetic inserts; a span emits inserts followed by
    // per-line deletes for the selected range
```

**Flow:** edits resolve in authored order against the ORIGINAL `fileLines` (a pre-pass inside `applyEdits`, before any line moves). A cut snapshots its range into the register and emits nothing; a gap paste becomes synthetic inserts; a span paste inserts replacement lines then per-line deletes for the span. `startClipboardBatch` copies only NAMED registers into a new batch; `commitClipboard` publishes only named-register changes back to a host-owned clipboard — anonymous state never escapes its batch.

**Invariant:** absent named register warns + no-ops for a gap but throws for a span (unless preview `drop` skips the paste); absent or ambiguous anonymous register throws by default. No empty paste may silently delete a span.

**Probe:** `test/clipboard.test.ts` covers cut/paste round trips, span replacement, empty-register behavior, and anonymous-paste ambiguity.

**Cross-capsule guard:** same-path sections merged ACROSS another file's section (`interleaved`) refuse clipboard ops at parse time (`CLIPBOARD_INTERLEAVED_SECTIONS`) — see `hashline-parser-seams.md`.

## Tree-sitter syntax proof: absence of proof is not a veto
**Path/Symbol:** `syntax.ts:nodeChain` (31–50), `enclosingBoundaries` (51+), `parsesCleanly` (87–105); native `enclosingBlockBoundaries`, `nodeChainAt`.
**Signature:** `nodeChain(lines, path, line): readonly NodeSpan[]`; `enclosingBoundaries(lines, path, startLine, endLine): readonly number[]`; `parsesCleanly(path, text): boolean`.
**Data Shape:** cache keys combine content hash, length, path, queried line/range; parse/boundary/chain caches are FIFO-bounded at `PARSE_CACHE_MAX = 256` (18).

### Decisive source
```ts
chain = nodeChainAt({ code: text, path, line }) ?? [];
boundaries = enclosingBlockBoundaries({ code: text, path, ranges }) ?? [];
// an unrecognized language, parse failure, or native failure returns []/false
```

**Flow:** boundary repair consults an innermost-first named-node chain and enclosing structural boundaries only when text evidence is insufficient. `parsesCleanly` deliberately conflates unknown language with parse failure so callers withhold structural rewrites rather than invent semantic conclusions; every miss caches too, so repeated queries are cheap but bounded.

**Invariant:** `[]` or `false` means NO structural evidence — never evidence that the source or proposed edit is wrong; only positive, path-aware parser results may support a structural repair.

**Probe:** `test/boundary-repair.test.ts` exercises parser-driven boundary decisions; `test/clipboard.test.ts` covers the edit expansion feeding the applier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(hasClipboardEdit|resolveClipboardEdits|startClipboardBatch|commitClipboard|validateClipboardSequence|nodeChain|enclosingBoundaries|parsesCleanly)$", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt original-order clipboard pre-pass with named/anonymous register isolation, throw-by-default empty pastes, and evidence-asymmetry for parser verdicts (positive proof only); adapt register persistence and parser runtimes to host; omit native bridge internals unless porting the whole engine. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk files.
