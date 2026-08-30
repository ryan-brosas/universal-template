<!-- capsule-v2 -->
# Chunked export iterator — how do I stream a large dataset out in bounded chunks with negative-index windows and cached totals?

**Source:** lh-basis (Linked Helper extract) **NO LICENSE — learn-only, pattern recorded, zero code copied**; Codebase Memory `lh-basis-source`. **Question:** what is the async-iterator contract for exporting N items in fixed-size chunks when start/end may be negative and total requires an async call?

## ExportIterator
**Path/Symbol:** `models/exportIterators/ExportIterator.js:ExportIterator` (constructor + `[Symbol.asyncIterator]`, `getLimitedTotal`, `normalizeStartAndEnd`, cached `getTotal`). Coverage caveat: this file sits outside the `lh-basis-source` project root — coverage check reports `missing`; claims are source-read at HEAD (whole file). Consumers confirmed via graph: `ProfilesSource.getCSVExportIterator`, `OrganizationProfilesSource.getCSVExportIterator`.
**Signature:** `new ExportIterator(source, chunkSize, start, end)` implementing `[Symbol.asyncIterator]() → { done, value }`; `start`/`end` accept negatives (Python-style from-end); `end === undefined` = open-ended.
**Data Shape:** each `next()` returns `{done, value: chunk[]}` where chunk ≤ chunkSize; iteration ENDS when an export returns zero rows (`done: iterationExportResult.length === 0`) OR start meets end.

### Decisive source (behavioral pseudocode — minified source read, not copied)
```
next():
    first call ⇒ normalizeStartAndEnd(start,end):      # resolve negatives ONCE against real total
        negative? start = max(total+start, 0); end likewise
    if start === end            → { done:true }
    iterationEnd = end ? min(end, iterStart+chunkSize) : iterStart+chunkSize
    chunk = await exportChunk(iterStart, iterationEnd)
    iterStart += chunkSize                              # advance even on short/empty chunks
    return { done: chunk.length === 0, value: chunk }   # dry page terminates too

getLimitedTotal():  clamp(total - offset, 0) then cap by window limit if limit > 0
getTotal():         memoized — exactly one upstream count per iterator lifetime
```

**Flow:** construct with window → first next() resolves absolute bounds from live total → loop pulls chunkSize slices until a slice comes back empty or the window closes → consumers (CSV export sources) just await the iterator.
**Invariant:** three termination conditions must coexist — closed window (`start===end`), empty chunk (upstream exhausted), and clamped math that never yields negative counts; total is fetched once and memoized so pagination cost is O(1) count calls regardless of chunk count. Negative indices are normalized exactly once, BEFORE any slicing.
**Probe:** no public tests — coverage caveat recorded. Adjacent tested seam in the same suite lane: Auto_job_applier's CSV helpers (4 stub tests) pin equivalent output-safety concerns.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "getCSVExportIterator", limit: 5 });
```

## Verdict
Adopt the contract: bounded-chunk async iteration over an offset window with one-shot memoized total, Python-style negative bounds, and dry-page termination; re-implement in your own language/runtime. **License boundary: source carries no license — record behavior, never copy code.**
