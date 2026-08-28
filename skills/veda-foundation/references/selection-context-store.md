<!-- capsule-v2 -->
# Selection-file context store — how do you persist a user's file/slice selection durably and concurrently-safely?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A CLI keeps a per-session list of selected files (with optional line slices) that feeds the model's context. How is that list stored, mutated under concurrency, and turned into prompt context?

## One text file of slice lines under the shared advisory lock
**Path/Symbol:** `src/context/store.ts:ContextStore` (whole, 246L); file format + glob resolution in `src/context/selection.ts` (`parseSelection` :10-23, `serializeSelection` :25-27, `readSelectionFile` :30-42, `writeSelectionFile` :45-48, `resolvePattern` :51-69); prompt serialization in `src/context/serialize.ts:serializeAllFileContextBlocks` (whole, 42L).
**Signature:** `store.add(patterns: string[]) → Promise<AddResult {added, skipped, notFound}>`; `store.remove(patterns) → Promise<RemoveResult {removed, notFound}>`; `store.list() → Promise<SelectionEntry[]>`; `store.tokens()/tokenDetails()`; `store.serialize() → Promise<string>`.
**Data Shape:** `SelectionEntry {original, absolutePath, slice: FileSlice}`; the file is one `path[:start[-end]]` line per entry (normalized via `formatSlice`); reads of a missing/corrupt file return `[]` (lenient-read contract, same as the stats logs).

### Decisive source
```ts
await withLock(this.selectionPath, async () => {
  const entries = await readSelectionFile(this.selectionPath, this.cwd);
  const existingPaths = new Set(entries.map(e => formatSlice(e.slice)));
  for (const path of resolvedPaths) {
    if (existingPaths.has(path)) {
      result.skipped++;
    } else {
      const slice = parseSlice(path);
      entries.push({ original: path, absolutePath: slice.path, slice });
      existingPaths.add(path);
      result.added++;
    }
  }
  await writeSelectionFile(this.selectionPath, entries);
});
```
Glob handling keeps the slice suffix per match:
```ts
const isGlob = basePath.includes('*') || basePath.includes('?') || basePath.includes('[');
if (isGlob) {
  const glob = new Bun.Glob(basePath);
  for await (const match of glob.scan({ cwd, absolute: true })) {
    matches.push(slice.sliceType === 'full' ? match : formatSlice({ ...slice, path: match }));
  }
}
```
**Flow:** `add` resolves each pattern (glob or literal) to absolute paths, drops not-found into the result (never throws), then under `withLock` dedupes against existing entries by normalized `formatSlice` form and appends → `remove` matches full-file patterns by path and sliced patterns by exact formatted string, rewrites the file under the lock → `tokens`/`tokenDetails` read every slice through `readSliceText` and sum `estimateTokensByScript` → `serialize` wraps successful reads in a `<file_context>` envelope with per-file fences and line-range annotations, silently dropping failed reads.
**Invariant:** every mutation happens inside one `withLock` on the selection file (the leaf's single advisory-lock primitive); dedupe is on the NORMALIZED form so `a.ts:1-3` and its formatted twin cannot double-add; failed reads degrade silently in `serialize` — a vanished file shrinks the context instead of failing the run.
**Probe:** `tests/context/store.test.ts` (executed live at pin: 16 pass / 0 fail) pins session-id validation, add/dedupe/not-found, slice entries, and removal; the performance note in the source records that list() caching was considered and deliberately NOT implemented ("inline until duplication appears").
**Coverage caveat:** no upstream test exercises concurrent add/remove races directly; the lock contract is inherited from the stale-lock-takeover capsule's source-pinned semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "ContextStore selection file add remove withLock resolvePattern serialize file_context", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-text-file selection store: lock-guarded read-modify-write, normalized-form dedupe, lenient reads, glob-with-slice-suffix resolution, and the `<file_context>` envelope. Adapt the path grammar to your slice syntax. Omit the token accounting if your host has no budget gate.
