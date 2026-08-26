<!-- capsule-v2 -->
# Vector encode pipeline — truncate → normalize → quantize ordering and the memmap spool

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** In what order must dense vectors be truncated, normalized and quantized, and how do large index builds stay under memory without losing crash recovery?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/vectors/base.py:Vectors.vectorize` (:357-392), `.index` (:112-153), `.vectors` (:155-189), `.quantize` (:453-479), `.vectorsid` (:248-262), `.spool` (:264-282); recovery `src/python/txtai/vectors/recovery.py:Recovery.__call__` (:39-57).
**Signature:** `vectors(documents, batchsize, checkpoint, buffer, dtype)` → `(ids, dimensions, embeddings-memmap)`.
**Data Shape:** batches of 500 docs encoded (encodebatch 32 per model call); embeddings streamed as .npy to a spool file; final array memmap'd `(len(ids), dimensions)`; dtype uint8 iff quantize else float32.

### Decisive source
```python
# vectorize — ORDER IS SEMANTICS
embeddings = self.encode(data, category)
if embeddings is not None:
    # Truncate embeddings, if necessary
    if self.dimensionality and self.dimensionality < embeddings.shape[1]:
        embeddings = self.truncate(embeddings)

    # Normalize data
    embeddings = self.normalize(embeddings)

    # Apply quantization, if necessary
    if self.qbits:
        embeddings = self.quantize(embeddings)
```
```python
# quantize: signed symmetric uint8 then keep low qbits
factor = 2 ** (self.qbits - 1)
scalars = embeddings * factor
scalars = scalars.clip(-factor, factor - 1) + factor
scalars = scalars.astype(np.uint8)
bits = np.unpackbits(scalars.reshape(-1, 1), axis=1)
bits = bits[:, -self.qbits :]
return np.packbits(bits.reshape(embeddings.shape[0], embeddings.shape[1] * self.qbits), axis=1)
```

**Flow (bulk):** documents stream in → per-batch `prepare` (optional tokenize + instruction prefix by category) → `recovery()` tries the checkpoint file first, on EOFError closes+deletes it and returns None → else live `vectorize` → np.save batch to spool → after stream ends, memmap the buffer and copy batches in → temp spool removed unless checkpointing. Checkpoint identity = uuid5 over the config subset `[path, method, tokenizer, maxlength, tokenize, instructions, dimensionality, quantize]` (+ vectors overrides) so a resumed run only replays matching-config batches.

**Invariant:** Truncate-BEFORE-normalize is load-bearing (MRL matryoshka truncation then renormalizes); normalize-before-quantize keeps the ±1 range that makes the symmetric uint8 scale correct. Recovery copies the checkpoint to a separate "recovery" file so the original checkpoint survives a second crash mid-resume.

**Probe:** `test/python/testembeddings.py:testTruncate` (:614-626), `testQuantize` (:381-394), checkpoint restart exercised via indexing with checkpoint dirs; `testvectors/testdense/testcustom.py:testIndex` (:38+) for external-vector passthrough (`batchtransform` skips encoding when input is already ndarray).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "vectorize truncate normalize quantize memmap checkpoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pipeline ordering + deterministic vectorsid + recovery-file copy semantics; adapt batch sizes; omit instructions/MRL truncation when unsupported by your model.
