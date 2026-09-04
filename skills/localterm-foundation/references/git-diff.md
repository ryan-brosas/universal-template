<!-- capsule-v2 -->
# Git diff pipeline — how do you surface a repo's diff (with untracked files) cheaply and reverse it safely?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you build per-file diff data (counts, statuses, patch bodies) under byte caps, and how do you undo an applied unified patch without silent corruption?

## Diff service — three parallel invocations over ONE diff queue
**Path/Symbol:** `packages/server/src/git-diff-service.ts:buildDiffCache` (209–353), `collectUntrackedFiles` (169–207), `resolveEffectiveBaseRef` (84–122), `ensureDiffCache` (355–369), `getGitDiffSummary` (371+).
**Signature:** `getGitDiff(cwd, {mode: "working"|"branch", base?})`; cache keyed `(cwd, mode, base)` via `readDiffCache`/`writeDiffCache` (git-diff-cache.ts).
**Data Shape:** caps from constants.ts: `GIT_MAX_PATCH_BYTES_PER_FILE`, `GIT_MAX_TOTAL_PATCH_BYTES`, `GIT_MAX_UNTRACKED_FILES/_FILE_BYTES/_TOTAL_BYTES`, `GIT_UNTRACKED_PATHS_MAX_BYTES`, `GIT_BINARY_SNIFF_BYTES`, `GIT_EMPTY_TREE_HASH`.

### Decisive source
```ts
// numstat + name-status (-z, NUL-delimited) are the source of truth for the
// file list; the patch output is keyed BY PATH not paired positionally — a
// symlink re-added as a regular file emits a deletion + an addition sharing
// one path, so numstat entries and diff --git blocks have no 1:1 mapping.
// (:163-172 comment; indexPatchesByPath concatenates multi-block patches)
const [numstatRes, nameStatusRes, patchRes] = await Promise.all([
  runGit(cwd, ["-c","core.quotepath=false","diff","--find-renames","--numstat","-z",baseRef]),
  runGit(cwd, [..."--name-status","-z",baseRef]),
  runGit(cwd, [..."--patch",baseRef], { maxStdoutBytes: GIT_MAX_TOTAL_PATCH_BYTES }),
]);
// branch mode diffs the MERGE-BASE of HEAD and base (not the tip); no explicit
// base resolves fork-PR upstream base from the PR cache before repo default.
```

**Flow:** read cache BEFORE resolving base ref (base resolution runs git on every call; warm per-file patch endpoint becomes a pure map lookup) → resolve baseRef (working ⇒ HEAD or empty tree when unborn) → three parallel git runs → parse numstat/name-status → key patches by path → fold untracked files in (`ls-files --others --exclude-standard -z` under count/byte caps, binary sniffed by NUL in first bytes, synthesized `@@ -0,0 +1,N @@` patches since git never lists untracked) → omit oversized patches with an explicit flag rather than failing.
**Invariant:** summary stays on the cheap numstat-only path unless a full cache already exists (pushed on every git-dirty signal); all three invocations share rename flags so counts/statuses/patches describe the same queue.
**Probe:** `packages/server/tests/git-diff.test.ts` :234 summarizes tracked/untracked/binary, :280 empty-tree base with no commits, :419 synthesizes an untracked text-file patch, :438 omits a patch exceeding the per-file cap, :481 branch mode compares to merge base.

## Parser — NUL-safe, quote-aware, path-keyed
**Path/Symbol:** `packages/server/src/git-diff-parser.ts:countLines/buildUntrackedPatch/splitPatchByFile/parseNumstatZ/parseNameStatusZ/indexPatchesByPath/unquoteGitPath/pathFromLine/extractPatchPath` (11–184).
**Signature:** `buildUntrackedPatch(content): string`; `parseNumstatZ(raw): NumstatEntry[]` where entries carry `oldPath` for renames and `binary` for `-` columns.
**Data Shape:** rename = 3 tokens after the entry; C-style quoted paths (`"p\ath"` with octal escapes) unquoted; a literal tab after an unquoted spaced path in `---/+++` lines stripped so keys align with numstat.

### Decisive source
```ts
export const buildUntrackedPatch = (content: string): string => {
  ...
  const noNewlineMarker = hasTrailingNewline ? "" : "\n\\ No newline at end of file";
  return `@@ -0,0 +1,${lines.length} @@\n${body}${noNewlineMarker}\n`;
};
// extractPatchPath: prefer +++ b/<path>; fall back to --- a/<path> (deletions);
// then "rename to <path>" for a pure rename with no content change at all. (:139-162)
```

**Flow:** split combined patch on `^(?=diff --git )` → extract new-side path per chunk (with /dev/null and pure-rename fallbacks) → concatenate multiple blocks sharing one path into one patch.
**Probe:** `tests/git-diff.test.ts` :113 renames parse old+new, :120 binary marked, :184 missing trailing newline marker, :394 single rename chunk returned.

## Reverse unified patch — verify-or-throw undo
**Path/Symbol:** `apps/harness/light-theme-rendering/reverse-unified-patch.mjs:reverseUnifiedPatch` (7–51).
**Signature:** `reverseUnifiedPatch(patchedSource, patchSource, filePath): string`.
**Data Shape:** locates the `diff --git a/<path> b/<path>` block, slices to the next block, walks hunks against the PATCHED source.

### Decisive source
```js
if (marker === " " || marker === "+") {
  if (patchedLines[patchedIndex] !== content)
    throw new Error(`Patch mismatch at ${filePath}:${patchedIndex + 1}: expected ${JSON.stringify(content)}`);
  if (marker === " ") restoredLines.push(content);   // context survives
  patchedIndex += 1;
} else if (marker === "-") restoredLines.push(content);  // removals come back
// "\ No newline at end of file" skipped; trailing un-hunked lines appended.
```

**Flow:** hunk header gives patched-side start → copy untouched prefix → walk hunk lines verifying context/added lines match the patched source (throw on mismatch), re-inserting removed lines → append tail.
**Invariant:** reversal is exact-or-exception — it never silently produces a corrupted restore. Coverage caveat: NO dedicated test file exists in-repo for this module (grep for `reverseUnifiedPatch` across tests returned nothing); claims are source-grounded only.
**Probe:** none available in-repo — port WITH your own round-trip test (apply → reverse → compare).

## Watcher — ref-snapshot change classification
**Path/Symbol:** `packages/server/src/git-diff-watcher.ts:buildGitSnapshot/classifyGitChanges` (98+/203–239).
**Signature:** `buildGitSnapshot(gitDir): GitSnapshot | null` (walks `refs/` up to `GIT_WATCHER_MAX_REFS = 10_000`, constants.ts:594); `classifyGitChanges(previous: GitSnapshot, current: GitSnapshot): GitRefEventName[]`.
**Data Shape:** snapshot of `.git` refs (HEAD + refs) → classified events: git-commit (branch advance, NOT branch creation/deletion), git-checkout (HEAD moved without a branch change), git-merge/git-cherry-pick/git-rebase (special refs present during the advance), git-reset (`ORIG_HEAD` appears without other special state), git-fetch (remote/fetch-head change), git-tag, git-stash.

### Decisive source
```ts
if (changes.branchAdvanced) {
  if (previous.special.mergeHead) events.push("git-merge");
  else if (previous.special.cherryPickHead) events.push("git-cherry-pick");
  else if (previous.special.rebaseMergeExists || previous.special.rebaseApplyExists)
    events.push("git-rebase");
  else if (changes.origHead && !branchSpecialStateBefore) events.push("git-reset");
  else events.push("git-commit");          // plain ref advance
} else if (changes.remote || changes.fetchHead) events.push("git-fetch");
if (changes.head && !changes.branch) events.push("git-checkout");
```

**Probe:** `tests/git-diff-watcher.test.ts` :69 advance vs :74 newly created branch, :89/:95/:101/:110 special-ref classes, :130 empty array when nothing changed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "reverseUnifiedPatch|indexPatchesByPath|buildUntrackedPatch|classifyGitChanges|buildDiffCache", limit: 8 });
```
Graph check this session: reverseUnifiedPatch resolved at apps/harness/light-theme-rendering/reverse-unified-patch.mjs 7–51, line-exact vs HEAD.

## Verdict
Adopt parallel-numstat/name-status/patch with by-path patch indexing, cache-before-base-resolution, capped untracked synthesis, verify-or-throw reversal, and ref-snapshot event classification; adapt cap values, git flags, and PR-cache integration to host; omit the browser diff-viewer UI and GitHub slug collection unless porting them. Probes cited from on-disk test files (vite-plus).
