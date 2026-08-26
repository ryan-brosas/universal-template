<!-- capsule-v2 -->
# Temporary directory lifecycle — when is the temp handle created, and why can't it be switched afterwards?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What governs lazy creation, path switching, and swap-space limits of the temporary directory?

## Lazy RequireTemporaryDirectory; switch forbidden once used; swap ceiling settable both before and after
**Path/Symbol:** `src/storage/standard_buffer_manager.cpp` — `SetTemporaryDirectory` (:64-71), `RequireTemporaryDirectory` (:485-497), `EncryptTemporaryFiles` (:498-500); state struct in header :188-198 (`mutable mutex lock`, `atomic<idx_t> size_on_disk`, `optional_idx maximum_swap_space`).
**Signature:** `void SetTemporaryDirectory(const string &new_dir)` throws `"Cannot switch temporary directory after the current one has been used"`; `void RequireTemporaryDirectory()` initializes the handle on first need.
**Data Shape:** `temporary_directory { string path; mutable mutex lock; atomic<idx_t> size_on_disk{0}; unique_ptr<TemporaryDirectoryHandle> handle; optional_idx maximum_swap_space; }`.

### Decisive source
```cpp
lock_guard<mutex> guard(temporary_directory.lock);
if (temporary_directory.handle)
    throw NotImplementedException("Cannot switch temporary directory after the current one has been used");
temporary_directory.path = new_dir;
...
void StandardBufferManager::RequireTemporaryDirectory() {
    if (temporary_directory.path.empty())
        throw InvalidInputException("Out-of-memory: cannot write buffer because no temporary directory is specified!...");
    lock_guard<mutex> guard(temporary_directory.lock);
    if (!temporary_directory.handle) {
        // temp directory has not been created yet: initialize it
        temporary_directory.handle = make_uniq<TemporaryDirectoryHandle>(db, path, size_on_disk, maximum_swap_space);
    }
}
```

**Flow:** startup stores only the PATH → first spill/read-back calls RequireTemporaryDirectory which materializes the handle under the lock → later SetTemporaryDirectory attempts throw because files already live on disk → swap-space limit applies to either the live file or the pending maximum.
**Invariant:** path mutation and handle creation share one mutex; encryption of temp files is a setting read at use time, so it must be fixed before the first spill.
**Probe:** `grep -c 'Cannot switch temporary directory after the current one has been used' src/storage/standard_buffer_manager.cpp` → `1`; `grep -n 'temp directory has not been created yet: initialize it' src/storage/standard_buffer_manager.cpp` → :492 comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "SetTemporaryDirectory RequireTemporaryDirectory TemporaryDirectoryHandle maximum_swap_space", limit: 10 });
```

## Verdict
Adopt lazy handle creation with a hard switch-after-use error; adapt your persistence boundary; omit encryption gating unless you spill ciphertext.
