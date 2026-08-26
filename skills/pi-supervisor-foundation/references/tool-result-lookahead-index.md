<!-- capsule-v2 -->
# Tool-result look-ahead index — why is call→result pairing a shared O(n) pre-scan instead of per-extractor scans?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do extractors find the tool_result belonging to a tool_call without tripling scan cost, and what window makes the pairing safe?

## buildToolResultIndex (`src/compaction/build-sections.ts`)
**Path/Symbol:** `src/compaction/build-sections.ts:buildToolResultIndex` (:19-33); `ToolResultIndex` interface `src/compaction/types.ts:4-6`.
**Signature:** `buildToolResultIndex(blocks): ToolResultIndex` with `get(callIndex): tool_result | null`.
**Data Shape:** Map from each tool_call block index → NEAREST following tool_result within `j < i+4` (window of 3 positions ahead).

### Decisive source
```ts
// Without this, files.ts / symbol-changes.ts / type-catalog.ts each scan
// forward independently — tripling the look-ahead cost and the regex parsing
// of tool results. The index collapses that to a single O(n) pre-scan.
for (let i = 0; i < blocks.length; i++) {
  if (blocks[i].kind !== 'tool_call') continue;
  for (let j = i + 1; j < Math.min(blocks.length, i + 4); j++) {
    if (blocks[j].kind === 'tool_result') { map.set(i, blocks[j]); break; }
  }
}
```

**Flow:** built once in `buildSections` (:311) and passed to the unified extractor; the fallback inline scan inside `extractFileAndSymbolData` (:301-308) reproduces IDENTICAL window semantics when no index is supplied, so both entry paths agree.
**Invariant:** (1) Window of +3 is the correctness bound: results farther than 3 blocks after their call are treated as unpaired rather than mispaired. (2) First-following-result wins — no attempt to match by call id. (3) The index maps CALL indexes only; a result with no preceding call in-window is simply never fetched. Porters who "fix" the window to unlimited will pair across unrelated turns.
**Probe:** direct test coverage rides the compaction suite: `tests/full-fidelity-snapshot.test.ts` `captures tool errors in outstanding context` (:172) exercises call→result adjacency through buildSections; graph pin `search_graph query:"buildToolResultIndex"` resolves `src/compaction/build-sections.ts 19-33`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "buildToolResultIndex look-ahead index nearest tool_result", limit: 8 });
```

## Verdict
Adopt bounded-lookahead pairing + single-shared-index for any multi-consumer transcript analysis. Adapt window size if your host interleaves thinking blocks between calls and results (count them!). Omit nothing else.
