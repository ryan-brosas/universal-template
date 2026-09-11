<!-- capsule-v2 -->
# Parser chunking kernel — how do oversized nodes become embeddable blocks without tiny remainders?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What are the size gates and the rebalancing rule for line-chunking when tree-sitter captures are missing or too big?

## Min/max gates + remainder-aware split search
**Path/Symbol:** `src/services/code-index/processors/parser.ts:parseContent/_chunkTextByLines` (:88-213 capture walk; :218-361 chunk kernel).
**Signature:** `_chunkTextByLines(lines: string[], filePath, fileHash, chunkType, seenSegmentHashes: Set<string>, baseStartLine = 1): CodeBlock[]`.
**Data Shape:** constants `MAX_BLOCK_CHARS=1000`, `MIN_BLOCK_CHARS=50`, `MIN_CHUNK_REMAINDER_CHARS=200`, `MAX_CHARS_TOLERANCE_FACTOR=1.15` → effectiveMax = 1150.

### Decisive source
```ts
if (currentChunkLength >= MIN_BLOCK_CHARS &&
    remainderLength < MIN_CHUNK_REMAINDER_CHARS &&
    currentChunkLines.length > 1) {
  // walk BACKWARD from the overflow line searching a split where BOTH sides clear floors
  if (potentialChunkLength >= MIN_BLOCK_CHARS && potentialNextChunkLength >= MIN_CHUNK_REMAINDER_CHARS) { splitIndex = k; break }
}
```

**Flow:** captures empty ⇒ whole-file fallback IF content ≥ 50 chars else nothing; node ≥50 chars but >1150 ⇒ recurse into children, leaf ⇒ line-chunk by node.type with `baseStartLine = startPosition.row+1`. Kernel: accumulate lines until adding one crosses 1150 → maybe rebalance (backward split-search so the NEXT chunk keeps ≥200 chars instead of starving) → finalize only chunks ≥50 chars. Oversized single LINES (>1150 chars) bypass chunks entirely: sliced into ≤1000-char `{type}_segment` blocks sharing start_line=end_line.
**Invariant:** every emitted block carries a dedupe `segmentHash` = sha256 of `${filePath}-${start}-${end}-${length}-${first100chars}` checked against ONE per-file `seenSegmentHashes` set — all four block factories (capture block, chunk, segment, markdown section) consult it, so identical blocks can never double-insert under the same point-id scheme.
**Probe:** `src/services/code-index/processors/__tests__/parser.spec.ts` ("_performFallbackChunking" :170+, "should chunk content when no captures are found"); executed pins: tolerance factor, remainder floor, 4× dedupe-guard greps.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CodeParser parseContent _chunkTextByLines _chunkLeafNodeByLines", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the four constants as a coupled set (they encode an embedding-size budget), the backward rebalancing search, and the segmentHash grammar — changing any hash input silently invalidates existing Qdrant points. Adapt language-specific capture selection. Omit vscode-free singleton export. Caveat: parser.spec mocks the tree-sitter layer; the rebalance loop itself has no dedicated spec (source-read verified).
