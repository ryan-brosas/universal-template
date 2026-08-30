<!-- capsule-v2 -->
# Temporary file offload — how do you spill fixed-size and variable-size blocks to one temp directory without corrupting counters?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What distinguishes the `.tmp` (fixed block) path from the `.block` (variable size) path, and where do evicted-byte counters change?

## Two-file-class spill; plaintext size header for big buffers; symmetric counter updates
**Path/Symbol:** `src/storage/standard_buffer_manager.cpp:WriteTemporaryBuffer` (:502-553), `ReadTemporaryBuffer` (:555-606), `DeleteTemporaryFile` (:608-651), `GetTemporaryPath` (:479-483).
**Signature:** `void WriteTemporaryBuffer(QueryContext, MemoryTag, block_id_t, FileBuffer&)`; `unique_ptr<FileBuffer> ReadTemporaryBuffer(QueryContext, MemoryTag, BlockHandle&, unique_ptr<FileBuffer>)`.
**Data Shape:** `.block` files: `header = sizeof(idx_t)*2 (+ DEFAULT_ENCRYPTED_BUFFER_HEADER_SIZE if encrypted)` storing `user_size` then `block_header_size` "in plaintext" for very large buffers; fixed-size blocks go through `GetTempFile()` shared handles instead.

### Decisive source
```cpp
if (buffer.AllocSize() == GetBlockAllocSize()) {          // fixed-size → grouped .tmp files
    idx_t eviction_size = ...->GetTempFile().WriteTemporaryBuffer(context, block_id, buffer);
    evicted_data_per_tag[uint8_t(tag)] += eviction_size;
    return;
}
// variable-size → own .block file: write size, header size, optional nonce/tag, then bytes
...
// ReadTemporaryBuffer: DeleteTemporaryFile already decrements evicted_data_per_tag for
// the .block path; do not decrement again here or the counter underflows on every read-back.
DeleteTemporaryFile(block.GetMemory());
```

**Flow:** write: RequireTemporaryDirectory → route by AllocSize → update per-tag eviction bytes exactly once; read: check in-memory temp buffers first (`HasTemporaryBuffer`) → else open the `.block`, read the two-word header, optionally decrypt, reconstruct, delete the file; delete: no-op when unloaded/dir missing, else reverse the counter delta.
**Invariant:** `evicted_data_per_tag[tag]` must be incremented on spill and decremented on reclaim EXACTLY once per byte-set — the read path deliberately skips its decrement because Delete does it.
**Probe:** `grep -c 'duckdb_temp_block-' src/storage/standard_buffer_manager.cpp` → `1`; `grep -n 'do not' src/storage/standard_buffer_manager.cpp | head -1` → :601 area ("decrement again here or the counter underflows on every read-back" at :602).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "WriteTemporaryBuffer ReadTemporaryBuffer GetTemporaryPath evicted_data_per_tag", limit: 10 });
```

## Verdict
Adopt dual-class spilling with a single-owner counter contract; adapt encryption hooks; omit DuckDB's specific EncryptionEngine calls if your temp files are plain.
