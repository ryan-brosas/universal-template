<!-- capsule-v2 -->
# Hashline parser seams — section splitting, lenient ranges, strict anchors

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you split a model-authored multi-section patch into lazily-parsed sections without trusting the model, and why are ranges forgiving while line anchors stay strict?

## Section splitting + same-path merging — structure first, parse lazily
**Path/Symbol:** `packages/hashline/src/input.ts:Patch` (427–462), `PatchSection` (246–418), `mergeSamePathSections` (~468–510); `packages/hashline/src/tokenizer.ts:splitHashlineLines` (94).
**Signature:** `Patch.parse(input, options?): Patch`; `Patch.parseSingle(input, options?): PatchSection`; `section.parse(): { edits, fileOp?, warnings }` (cached).
**Data Shape:** sections rooted at `[PATH#HASH]` headers carrying `path`, `fileHash?`, raw `diff`, `#interleavedMerge`; edits parse lazily per section and cache one `{ edits, fileOp?, warnings }`.

### Decisive source
```ts
static parse(input: string, options: SplitOptions = {}): Patch {
  const raw = mergeSamePathSections(splitRawSections(input, options));
  return new Patch(raw.map(section => new PatchSection(section)));
}
// in PatchSection.parse():
if (this.#interleavedMerge && hasClipboardEdit(parsed.edits)) {
  throw new Error(CLIPBOARD_INTERLEAVED_SECTIONS);
}
```

**Flow:** the splitter walks lines recognizing `[PATH#HASH]` headers (unquoting `"path"`/`'path'`) and strips apply_patch-style verb noise (`Update File:`, `Add File:`, `Move to:`, duplicated `***`) models reflexively prepend; a best-effort bracketed-header recovery path runs when the strict tokenizer rejects. Consecutive **or interleaved** sections for the same path merge into one section with concatenated diffs — conflicting snapshot tags on the same path throw (`Conflicting hashline snapshot tags … Re-read the file`). Parsing stays per-section and cached so preflight/apply/diff-preview share one result; an interleaved merge carrying clipboard ops refuses determinism-breaking reorder.

**Invariant:** splitting is purely structural and never checks that a path exists (that is the patcher's job); anchors authored against one file snapshot must apply as ONE batch, which is exactly why same-path sections merge before any edit lands.

**Probe:** `test/core-contracts.test.ts` (input splitter, strict parse errors), `test/patcher.test.ts` (same-tag integrity across merged sections).

## Lenient ranges, strict line anchors
**Path/Symbol:** `tokenizer.ts:scanRangeSeparator` (163–193), `parseLid` (139–150).
**Signature:** `parseLid(raw, lineNum): Anchor`; `scanRangeSeparator(line, index, end): number | null`.

### Decisive source
```ts
const number = scanLineNumber(raw, numberStart, end);
if (number === null || skipWhitespace(raw, number.nextIndex, end) !== end) {
  throw new Error(
    `line ${lineNum}: expected a line number such as ${describeAnchorExamples("119")}; got ${JSON.stringify(raw)}. Use ${HL_FILE_PREFIX}PATH${HL_FILE_HASH_SEP}hash${HL_FILE_SUFFIX} from your latest read for file-version binding.`,
  );
}
return { line: number.line };
```

Ranges parse deliberately lenient: canonical `.=` but `-`, `=`, `.`, `..`, `…`, mixed runs, and whitespace-only separators recover to the same range; even a dangling separator run (`244.=:`, `5-`) collapses to an open range `N.=N` when followed by `:`/`@`/end-of-header (`scanDanglingSeparator`). Line anchors are the opposite: bare unsigned decimal scanning to end-of-token only (integer overflow rejected via SafeInteger guard), and the thrown error names both the accepted shape (`describeAnchorExamples`) and the fix (re-read the file for the current hash).

**Invariant:** ranges forgiving, anchors strict — a bare number is only ever a line; separators never reshape edits.

**Probe:** `test/leniency.test.ts` (range/header/dangling-separator recovery), `test/format-v2.test.ts` (anchor phrasing), `test/core-contracts.test.ts` (strict anchor rejection message).

## Snapshot store — read-through cache keyed by canonical path
**Path/Symbol:** `packages/hashline/src/snapshots.ts:SnapshotStore` (54–112), `InMemorySnapshotStore` (155+).
**Signature:** `SnapshotStore.read(path): Promise<Snapshot>`; `byHash(path, hash)` returns the latest retained text on a tag collision.
**Data Shape:** snapshots keyed by `canonicalPath` (from the `Filesystem.canonicalPath` override) carry path + lastWrite; multiple texts per tag (colliders) are retained.

**Decisive shape:** producers and consumers agree on keys even when authored paths differ (viewer-relative vs absolute). Snapshots speed up diff/show/recovery; stale or missing ones degrade to live reads — never a patching source of truth.

**Invariant:** snapshots are advisory, never authoritative. Patches apply against live content; retention bounds the proof window available to `Recovery.tryRecover`.

**Probe:** `test/snapshots.test.ts` (cache staleness, canonical key, collider retention).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(Patch|PatchSection|mergeSamePathSections|parsePatch|parsePatchStreaming|parseLid|scanRangeSeparator|scanDanglingSeparator|splitHashlineLines|SnapshotStore)$", limit: 12, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.input.Patch" });
```

## Verdict
Adopt lazy per-section parsing with same-path merging + conflicting-tag rejection, the lenient-range/strict-anchor duality, actionable anchor errors naming the fix, and the canonical-keyed advisory snapshot store; adapt header noise patterns, separator alphabet, and storage of snapshots to host; omit the streaming parser variant until a target needs incremental previews. Coverage caveat: tests excluded from graph index by design; probes are source-grounded from on-disk files.
