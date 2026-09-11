<!-- capsule-v2 -->
# Mnemonic vector internals — int8/bit store, Hamming+cosine, triples split

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/mnemopi/src/core/binary-vectors.ts`, `vector-math.ts`, `migrations/`. **Question:** How do you trade embedding precision for storage/search speed safely, and migrate a legacy table behind backup + dry-run?

## Vec type: float32 / int8 / bit, env-driven
**Path/Symbol:** `binary-vectors.ts:getVecType` (101–107), `VEC_TYPE` (109), `quantizeInt8` (111–118), `maximallyInformativeBinarization` (120–131), `hammingDistance` (133–148), `informationTheoreticScore` (171), `BinaryVectorStore` (178+), `FastBinarySearch` (278+, `src/migrations/e6-triplestore-split.ts` sibling file).
**Signature:** `getVecType(env?): VecType` — `MNEMOPI_VEC_TYPE` (float32|int8|bit; default int8; invalid → float32); `quantizeInt8(embedding): Int8Array` — saturate clamp then round; `maximallyInformativeBinarization(embedding): Uint8Array` — bit per dim, byte = `i>>3`, bitmask `7-(i&7)`.
**Data Shape:** rows `{ memory_id, binary_vector: Uint8Array|ArrayBuffer|Buffer, original_dim, magnitude }`; result `{ memory_id, distance, score }`; stats `{ total_vectors, avg_bytes_per_vector, compression_ratio, … }`.

### Decisive source
```ts
const POPCOUNT_TABLE = new Uint8Array(256);  // byte → set-bit count
// hammingDistance: XOR shared bytes, sum via popcount table
// cosineSimilarity (vector-math.ts): missing dims = 0; zero-norm → 0
```

**Flow:** storage inherits the vec type at import; float32 keeps exact cosine; int8 halves footprint via saturating quantization; bit packs `ceil(dim/8)` bytes and searches ONLY by Hamming distance. `BinaryVectorStore` persists BLOB rows in SQLite and inserts + best-matches; `FastBinarySearch` scans row blobs against the popcount table with parity asserted across encodings in `native-vector-parity`.

**Invariant:** encodings are pairwise-lossy only through the given quantizer — cosine exact for float32, approximate for int8, Hamming-only for bit; zero-norm scores 0, never NaN.

**Probe:** `test/binary-vectors.test.ts`, `test/vector-index.test.ts`, `test/native-vector-parity.test.ts`, `test/e5a-vector-voice-dense-rewire.test.ts`, `test/degrade-vector.test.ts`. Coverage caveat: tests excluded from graph index by design.

## Migrations — triples split behind backup + dry-run
**Path/Symbol:** `migrations/e6-triplestore-split.ts:ANNOTATION_KINDS` (5), `MigrationOptions` (8: `{ dbPath, dryRun?, backup?, logFn? }`), `placeholders` (35), `hasTable` (39).

### Decisive source
```ts
export const ANNOTATION_KINDS = ["mentions", "fact", "occurred_on", "has_source"] as const;
// copyDatabase: serialize() of a read-write handle → backup before split
// rows read in placeholders-chunked batches, reinserted per annotation kind
```

**Flow:** runs only when the legacy `triples` table exists; optionally dry-runs, optionally backs up the whole DB via SQLite `serialize()`, then migrates rows into per-kind typed tables. Idempotent by construction.

**Probe:** `tests/migrate-triplestore-split.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(getVecType|quantizeInt8|maximallyInformativeBinarization|hammingDistance|FastBinarySearch|cosineSimilarity)$", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt env-driven vec-type selection with per-type search semantics and popcount-table Hamming scan; adapt the env var name, default type, and dims to host; omit SQLite persistence specifics if another vector store is available.
