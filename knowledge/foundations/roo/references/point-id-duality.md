<!-- capsule-v2 -->
# Point-ID duality — which identity grammar does each write path use for Qdrant points?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What UUID namespace and name string does the scanner vs the watcher use, and why does it matter for upserts?

## uuidv5 over two DIFFERENT name strings
**Path/Symbol:** `src/services/code-index/processors/scanner.ts:processBatch` (:424) vs `src/services/code-index/processors/file-watcher.ts:processFile` (:472-473); shared namespace `QDRANT_CODE_BLOCK_NAMESPACE = "f47ac10b-58cc-4372-a567-0e02b2c3d479"` (constants/index.ts:14).
**Signature:** `uuidv5(block.segmentHash, QDRANT_CODE_BLOCK_NAMESPACE)` vs `uuidv5(\`${normalizedAbsolutePath}:${block.start_line}\`, QDRANT_CODE_BLOCK_NAMESPACE)`.
**Data Shape:** scanner payload carries `segmentHash`; watcher payload does NOT.

### Decisive source
```ts
// scanner.ts:424 — content-derived identity
const pointId = uuidv5(block.segmentHash, QDRANT_CODE_BLOCK_NAMESPACE)
// file-watcher.ts:472-473 — position-derived identity
const stableName = `${normalizedAbsolutePath}:${block.start_line}`
const pointId = uuidv5(stableName, QDRANT_CODE_BLOCK_NAMESPACE)
```

**Flow:** scanner IDs change when a block's content/lines/length/preview change ⇒ an edited block gets a NEW point id while delete-by-file-path removes the OLD ones first (delete-before-upsert). Watcher IDs are stable per (file,line), so re-upserting the same start line OVERWRITES in place — but two distinct segments starting on one line would collide.
**Invariant:** never mix grammars in one collection without mapping: the same logical block can exist under TWO ids (old scanner hash + new position hash), doubling results. The segmentHash input grammar (`filePath-start-end-length-preview100`) must match byte-for-byte across writer versions or dedupe silently breaks.
**Probe:** deterministic pins executed: `uuidv5(block.segmentHash` at scanner :424; `` ${normalizedAbsolutePath}:${block.start_line} `` at watcher :472; adversarial greps prove neither file contains the other's grammar.
**Retrieve:** (drift note 2026-08-24 pass 7: multi-token query regressed to total:0 — repaired to search_code, live-resolved)
```bash
codebase-memory-mcp cli search_code '{"project":"Roo-Code","pattern":"QDRANT_CODE_BLOCK_NAMESPACE"}'
# Variable row src/services/code-index/constants/index.ts 14 + usage rows: FileWatcher.processFile :473, DirectoryScanner.processBatch :424
```
## Verdict
Adopt ONE grammar deliberately; if porting both paths, normalize to the scanner's content-hash identity (it composes with delete-before-upsert). Adapt the namespace UUID per product. Omit nothing else — this is a two-line contract whose violation is silent data duplication.
