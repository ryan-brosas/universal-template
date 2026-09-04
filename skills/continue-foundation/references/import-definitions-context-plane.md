<!-- capsule-v2 -->
# Import-definitions context plane — precalculated LRU keyed on active editor, first-100-rows AST import scan, cursor-window symbol match

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does autocomplete pull in the DEFINITIONS of symbols the user just imported, and what does the caching/parse strategy look like so it stays cheap?

## Key facts
**Path/Symbol:** `core/autocomplete/context/ImportDefinitionsService.ts` (whole, 113L) + facade `ContextRetrievalService.ts` (whole, 99L, `getSnippetsFromImportDefinitions` :28-63); cache primitive `PrecalculatedLruCache` (`core/util/LruCache.ts`, N=10 via `ImportDefinitionsService.N`).
**Signature:** `get(filepath): FileInfo | undefined`; private `_getFileInfo(filepath): Promise<FileInfo | null>`; facade `initializeForFile(filepath)` for out-of-band flows.
**Data Shape:** `FileInfo = {imports: {[symbol]: RangeInFileWithContents[]}}`; snippet window = last 5 prefix lines + first 3 suffix lines; AST parsed ONLY over `includedRanges` rows 0–100 / bytes 0–10_000.

### Decisive source
```ts
// :24-33 — the cache warms on ACTIVE-EDITOR CHANGE, not on request:
ide.onDidChangeActiveTextEditor((filepath) => {
  this.cache.initKey(filepath).catch((e) => console.warn(...));
});

// :68-77 — imports live at the top: parse only the head of the file
const ast = parser.parse(fileContents, undefined, {
  includedRanges: [{ startIndex: 0, endIndex: 10_000,
    startPosition: { row: 0, column: 0 }, endPosition: { row: 100, column: 0 } }],
});
// :40-42 — .ipynb excluded (upstream links issue #1463)
if (filepath.endsWith(".ipynb")) return null;

// ContextRetrievalService :40-45 — which imported symbols matter? the ones VISIBLE near cursor:
const textAroundCursor = helper.fullPrefix.split("\n").slice(-5).join("\n") +
                         helper.fullSuffix.split("\n").slice(0, 3).join("\n");
const symbols = Array.from(getSymbolsForSnippet(textAroundCursor))
  .filter((symbol) => !helper.lang.topLevelKeywords.includes(symbol));
```

**Flow:** active tab change → LRU pre-warms that file's import map (tree-sitter import queries per language → gotoDefinition per captured symbol → read each definition range); at completion time the facade extracts identifiers from the ±cursor text window, drops language top-level keywords, and emits each matching import's definition contents as an AutocompleteCodeSnippet. Missing parser or missing query file ⇒ empty map, never an error.

**Invariant:** freshness rides EDITOR FOCUS, not keystrokes — a porter who moves warming to request time reintroduces gotoDefinition latency into the completion path; one who caches forever serves stale definitions after edits. The 100-row parse cap is the entire cost story: files whose imports sit below row 100 get silently empty maps (accepted trade-off, not a bug). Notebook exclusion is load-bearing history (#1463).

**Probe:** `grep -c 'initKey' core/autocomplete/context/ImportDefinitionsService.ts` → 1 (:26 editor-change warm; ContextRetrievalService's facade adds a second via `(this.importDefinitionsService as any).cache.initKey`); `grep -c 'endIndex: 10_000' core/autocomplete/context/ImportDefinitionsService.ts` → 1; `grep -c 'row: 100' core/autocomplete/context/ImportDefinitionsService.ts` → 1; `grep -c 'slice(-5)' core/autocomplete/context/ContextRetrievalService.ts` → 1.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "ImportDefinitionsService PrecalculatedLruCache initKey getSnippetsFromImportDefinitions", limit: 8 })`

## Verdict
Adopt focus-triggered precalculation plus the tiny head-of-file import parse and the cursor-window symbol filter. Adapt N (LRU size), the 100-row cap, and the keyword blacklist to your languages.
