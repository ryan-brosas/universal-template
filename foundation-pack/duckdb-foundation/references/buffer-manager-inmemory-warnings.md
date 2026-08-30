<!-- capsule-v2 -->
# In-memory mode warnings — what must an engine tell users who never set a temp directory but hit memory limits?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Where is the in-memory remediation text generated, and how do temp-file listings stay race-safe?

## InMemoryWarning postscript; NULL_IF_NOT_EXISTS open; per-tag evicted-bytes ledger
**Path/Symbol:** `src/storage/standard_buffer_manager.cpp` — `InMemoryWarning` (:704-714), `GetMemoryUsageInfo` (:467-480), `SetMaxSwapSpace` (:458-464), temp-file census `GetTemporaryFiles` (:672-699).
**Signature:** `static const char *InMemoryWarning()` returns "" when a temp dir exists, else the multi-line hint ending `SET temp_directory='/path/to/tmp.tmp'`.
**Data Shape:** `evicted_data_per_tag[MEMORY_TAG_COUNT]` atomics indexed by MemoryTag; `TemporaryFileInformation {path, size}`.

### Decisive source
```cpp
const char *StandardBufferManager::InMemoryWarning() {
    if (!temporary_directory.path.empty()) return "";
    return "\nDatabase is launched in in-memory mode and no temporary directory is specified."
           "\nUnused blocks cannot be offloaded to disk."
           "\n\nLaunch the database with a persistent storage back-end"
           "\nOr set SET temp_directory='/path/to/tmp.tmp'";
}
// GetTemporaryFiles: another process/thread can delete the file before we stat it —
auto handle = fs.OpenFile(name, FILE_FLAGS_READ | FILE_FLAGS_NULL_IF_NOT_EXISTS);
if (!handle) return;
```

**Flow:** every OutOfMemoryException raised by EvictBlocksOrThrow appends the postscript (empty when spilling is possible) → admin surfaces read per-tag usage plus evicted bytes and enumerate `.block`/`.tmp` files tolerating deletion races.
**Invariant:** the postscript is empty exactly when offloading is available — OOM text must never recommend a temp directory to someone who already has one.
**Probe:** `grep -c 'Unused blocks cannot be offloaded to disk' src/storage/standard_buffer_manager.cpp` → `1`; `grep -c 'FILE_FLAGS_NULL_IF_NOT_EXISTS' src/storage/standard_buffer_manager.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "InMemoryWarning GetMemoryUsageInfo evicted_data_per_tag GetTemporaryFiles", limit: 10 });
```

## Verdict
Adopt context-aware OOM remediation text and race-tolerant file censuses; adapt tag names; omit the swap-space ceiling if your storage has none.
