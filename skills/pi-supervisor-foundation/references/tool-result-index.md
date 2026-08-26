<!-- capsule-v2 -->
# Tool-result index — one O(n) call→result look-ahead index replacing three independent forward scans

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do multiple extractors share tool-result lookups without each re-scanning the block list?

## Pre-built look-ahead map
**Path/Symbol:** `src/compaction/build-sections.ts:19-33` (`buildToolResultIndex`), consumed by `extractFileAndSymbolData(blocks, tri)` :317.
**Signature:** `buildToolResultIndex(blocks: NormalizedBlock[]): ToolResultIndex` where `ToolResultIndex = { get(callIndex: number): ToolResultBlock | null }`.
**Data Shape:** Map from tool_call block index → nearest following tool_result within a **+3 position window** (`j < Math.min(blocks.length, i + 4)`).

### Decisive source
```ts
const buildToolResultIndex = (blocks: NormalizedBlock[]): ToolResultIndex => {
  const map = new Map<number, Extract<NormalizedBlock, { kind: 'tool_result' }>>();
  for (let i = 0; i < blocks.length; i++) {
    if (blocks[i].kind !== 'tool_call') continue;
    for (let j = i + 1; j < Math.min(blocks.length, i + 4); j++) {
      if (blocks[j].kind === 'tool_result') { map.set(i, blocks[j]); break; }
    }
  }
  return { get: (callIndex: number) => map.get(callIndex) ?? null };
};
```
The in-source comment records WHY (:11-18): without it, files/symbol-changes/type-catalog each scanned forward independently — tripling look-ahead cost and regex parsing; the index collapses that to one O(n) pre-scan.

**Flow:** buildSections builds the index once (unless injected via optional `input.toolResultIndex`) → unified extractor resolves each read/write call's result through `tri.get(i)` → no extractor ever walks forward itself.
**Invariant:** The +3 window is part of the contract: results further than 3 positions after the call are treated as unpaired (protects against misattribution across interleaved calls). First result inside the window wins.
**Probe:** `grep -cn "i + 4" src/compaction/build-sections.ts src/compaction/extract/shared-symbols.ts` → 1 line each (index build + fallback twin). Direct test: `tests/full-fidelity-snapshot.test.ts:142` describe('buildCompactionSummary') exercises the whole pipeline including pairing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "buildToolResultIndex look-ahead", limit: 10 });
```

## Verdict
Adopt shared look-ahead indexing whenever ≥2 consumers pair calls to results over the same stream. Adapt window size to your host's message granularity (call+result adjacency differs per transport). Omit the inline fallback twin only if you control all call sites.
