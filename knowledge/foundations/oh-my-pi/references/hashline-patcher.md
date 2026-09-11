<!-- capsule-v2 -->
# Hashline Patcher orchestration — how do you apply multi-section content-hash-tagged patches all-or-nothing?

**Source:** Oh My Pi MIT `main@96f42809764f0907f7d6b115eab5710de28941de`; Codebase Memory `oh-my-pi`. **Question:** How do you orchestrate parse → tag validation → in-memory apply → write so a stale snapshot tag can never silently corrupt a file, and a failed batch never leaves ambiguity about what landed?

## Prepare-everything-then-commit patcher over a pluggable Filesystem + SnapshotStore
**Path/Symbol:** `packages/hashline/src/patcher.ts:Patcher` (217–759) — `apply` (243–300), `prepare` (350–429), `commit` (469–575), `#applyWithRecovery` (673–758), `#assertSeenLines` (622–654), `#recoverSectionPathFromTag` (444–461); `PatcherOptions` (68–91), `PatchSectionResult` (94–130), `PreparedSection` (141–160); constants `SEEN_LINE_REVEAL_CAP = 40` (56), `SEEN_LINE_REVEAL_MAX_COLUMNS = 512` (66).
**Signature:** `class Patcher { constructor(options: PatcherOptions); apply(patch: Patch): Promise<PatcherApplyResult>; preflight(patch: Patch): Promise<void>; prepare(section: PatchSection, clipboard?: Clipboard): Promise<PreparedSection>; commit(prepared: PreparedSection): Promise<PatchSectionResult>; }`.
**Data Shape:** options: required `fs: Filesystem` + `snapshots: SnapshotStore` (constructor throws without it — tags are opaque store pointers); optional `blockResolver`, `enforceSeenLines? = true`, host-owned `clipboard`. Per-section result carries `op ∈ {create, update, delete, noop}`, before/after/persisted/written text, `fileHash` (4-hex), fresh `[path#tag]` header, warnings, `firstChangedLine`, optional `blockResolutions`.

### Decisive source
```ts
// apply(): prepare every section first — any failure (stale hash, missing
// file, parse error, in-memory no-op) surfaces BEFORE any write.
for (const section of patch.sections) {
    prepared.push(await this.prepare(section, clipboard));
    sectionStates.push(forkClipboard(clipboard));   // register state per landed prefix
}
assertUniqueCanonicalPaths(prepared);               // "Merge their ops under one header"
// commit(): the FS adapter reports what actually landed on disk. Keying the
// snapshot on the pre-write text would record a hash for content that no
// longer exists — the mechanism behind "single-line edit reformats the whole
// file". Re-derive and hash THAT; drift itself is a warning, not a diff.
const recorded = normalizeToLF(stripBom(write.text).text);
const driftedOnWrite = recorded !== after;
const fileHash = this.#recordFullSnapshot(canonicalPath, recorded);
```

**Flow:** `prepare`: parse (with block-range diagnostic enrichment via the resolver) → require the section tag → canonicalize path → read; if missing, try filename+tag path recovery (`findByHash` ∩ same basename, exactly one candidate, excluding the authored path's own record, gated by `fs.allowTagPathRecovery`) → run `fs.preflightWrite` on the FINAL target (write gate wins over not-found) → strip BOM / detect+normalize line endings → `#applyWithRecovery`. `#applyWithRecovery`: live hash equals tag ⇒ seen-line guard then direct apply; no anchor-scoped edits on drift ⇒ head/tail insert applies with `HEADTAIL_DRIFT_WARNING`; else `Recovery.tryRecover` remaps anchors from tagged snapshot to unchanged live lines; failure ⇒ `MismatchError` with dual hashes (`hashRecognized` picks drift vs fabrication branch). `commit`: delete/noop fast paths → restore BOM+CRLF → write → re-hash what actually landed → record fresh snapshot. Mid-batch write failure throws listing "Sections already written / not written" so the caller can re-issue only the missing ones instead of double-applying.
**Invariant:** no write touches disk until every section applied in memory (naturally all-or-nothing reads; commits are NON-atomic and honestly reported); duplicate canonical targets are rejected before any commit; every returned tag hashes post-write disk truth, so follow-up edits validate against reality even when format-on-save drifted the bytes; noop results are errors, not successes ("resulted in no changes being made").
**Probe:** `packages/hashline/test/patcher.test.ts:169` (DriftingFilesystem converts spaces to tabs on write; returned tag MUST equal `computeFileHash(onDisk)` and a follow-up edit anchored on it succeeds); `:234` (stale-tag head/tail insert warns instead of failing); `:268` (anchor on a line the read never displayed rejects with "never displayed"); `:307/:332/:372` (reveal-unblocks-retry vs cap-truncated reveal keeps merge gate closed); `packages/coding-agent/test/core/hashline.test.ts:184` ("preflights every section before writing multi-file edits" — both files untouched after a bad second section), `:210` (duplicate canonical targets rejected).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^Patcher$", limit: 5, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.patcher.Patcher" });
```

## Verdict
Adopt the two-layer prepare/commit split, the write-time re-hash onto disk truth, the unique-canonical-path gate, the non-atomic-commits landed-prefix report, and the seen-line provenance guard (40-line/512-col reveal caps with all-or-nothing merging — it kills piecewise blind-edit retries); adapt the Filesystem/SnapshotStore backends, warning texts, and recovery policy knobs to your host; omit the ACP-bridge specifics and the tree-sitter `replace_block` resolver unless your host needs block anchors.
