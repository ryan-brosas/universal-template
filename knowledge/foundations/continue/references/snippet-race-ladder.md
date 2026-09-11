<!-- capsule-v2 -->
# Snippet race ladder — how does the snippet plane stay under the latency budget without dropping the whole payload?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When gathering context snippets for a completion, which sources are raced against a timeout, what does a lost race yield, and why do two variants of the gatherer exist?

## The 100ms per-source race over one Promise.all
**Path/Symbol:** `core/autocomplete/snippets/getAllSnippets.ts:getAllSnippets` (:169-218), `racePromise` (:31-37), `getSnippetsFromRecentlyOpenedFiles` (:110-167).
**Signature:** `getAllSnippets({helper, ide, getDefinitionsFromLsp, contextRetrievalService}): Promise<SnippetPayload>`; `racePromise<T>(promise: Promise<T[]>, timeout = 100): Promise<T[]>`.
**Data Shape:** returns `SnippetPayload` of nine typed arrays (rootPath, importDefinition, ide, recentlyEditedRange, recentlyVisitedRange, diff, clipboard, recentlyOpenedFile, static); each source independently degrades to `[]`.

### Decisive source
```ts
function racePromise<T>(promise: Promise<T[]>, timeout = 100): Promise<T[]> {
  const timeoutPromise = new Promise<T[]>((resolve) => {
    setTimeout(() => resolve([]), timeout);
  });
  return Promise.race([promise, timeoutPromise]);
}
```
```ts
// Cut off at 80ms via racing promises — per-file inside the parallel batch
return Promise.race([
  readPromise,
  new Promise<null>((resolve) => setTimeout(() => resolve(null), 80)),
]);
const results = await Promise.all(fileReadPromises);
return results.filter(Boolean) as AutocompleteCodeSnippet[];
```
```ts
ideSnippets: IDE_SNIPPETS_ENABLED ? racePromise(getIdeSnippets(...)) : [],   // const IDE_SNIPPETS_ENABLED = false
[], // racePromise(getDiffSnippets(ide)) // temporarily disabled, see PR #5882
recentlyVisitedRangesSnippets: helper.input.recentlyVisitedRanges,           // synchronous pass-through
```

**Flow:** seven sources fan out under ONE `Promise.all` — rootPath / importDefinition / ide / diff / clipboard / recentlyOpenedFiles / static-context. Each async source is individually raced at **100 ms**, resolving to `[]` on loss; the recently-opened-files reader races EACH FILE read at **80 ms** and resolves losers to `null` (filtered after). Recently-edited ranges are built synchronously from input; recently-visited ranges are passed through untouched; static context is opt-in via `experimental_enableStaticContextualization`; IDE-LSP snippets sit behind a hard-coded `false` flag and diffs behind an explicit disabled slot citing PR #5882.
**Invariant:** A slow source degrades to EMPTY ARRAY, never blocks the payload, and never rejects (the whole `getAllSnippets` would otherwise fail the completion). The race resolves the VALUE `[]`, not an error — porters who substitute `Promise.any` or rethrow timeouts break every completion where any provider is slow. `getAllSnippetsWithoutRace` (:220-267) is byte-for-byte the same fan-out WITHOUT `racePromise` wrappers — it exists so nextEdit's offline context mirror can wait for full fidelity.
**Probe:** `gitDiffCache.vitest.ts` pins the cache layer feeding `getDiffsFromCache` ("returns empty array on error" :34); deterministic source probe: `grep -c 'racePromise' getAllSnippets.ts` → 8 call sites + definition; the two variants differ ONLY by the `racePromise(` wrapper (verified by reading both bodies).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "getAllSnippets racePromise SnippetPayload", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-source value-degrading races (100 ms outer, 80 ms per-file) over one Promise.all and the sync pass-through for already-known ranges; adapt timeouts and the source list to your latency budget; omit the disabled ide/diff slots unless reviving those surfaces. Coverage caveat: no direct unit suite for `racePromise`; behavior pinned by source + the gitDiffCache test that exercises its error path.
