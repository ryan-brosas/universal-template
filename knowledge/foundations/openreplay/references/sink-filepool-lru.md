<!-- capsule-v2 -->
# Sink FilePool LRU + size cap — how do you write thousands of concurrent session files without exhausting FDs?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What eviction, append-detection, and fsync policy must a session-file writer copy?

## Least-recently-used fd pool with O_APPEND reopen
**Path/Symbol:** `backend/internal/sink/sessionwriter/filepool.go` — `Write` (:90–111), `ensureOpen` (:113–137), `evictOne` (:139–156), `Sync` (:158–217), `fileEntry.write/sync` (:34–56).
**Signature:** `FilePool.Write(path string, header, data []byte) error`; `Sync() SyncStats`.
**Data Shape:** `entries map[path]*fileEntry` capped at `limit`; `lastUse map[path]int64` (ns); entry = `{file *os.File, buffer *bufio.Writer, size int64, updated bool}`; `maxFileSize>0` ⇒ hard cap (`ErrSizeLimitExceeded`).

### Decisive source
```go
if len(p.entries) >= p.limit { p.evictOne() }
f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
...
entry := &fileEntry{ file: f, buffer: bufio.NewWriterSize(f, p.bufSize), size: info.Size() }
return entry, info.Size() == 0, nil   // isNew ⇔ file was empty
```

**Flow:** Write → ensureOpen (reopen appends to existing file: `size` seeded from Stat so headers are written only when `isNew`) → buffered write → periodic Sync drains dirty entries via N worker goroutines → CloseFile/Stop flush+close. Eviction closes the least-recently-used fd and drops it from both maps.
**Invariant:** Header write is keyed on `info.Size()==0`, NOT on a new-entry flag — after crash/restart the same path resumes appending without duplicating the header. Eviction under lock must close before delete or fds leak.
**Probe:** `grep -c 'ErrSizeLimitExceeded' backend/internal/sink/sessionwriter/filepool.go` → `2`; `grep -c 'os.O_APPEND' backend/internal/sink/sessionwriter/filepool.go` → `1`; `grep -c 'info.Size() == 0' backend/internal/sink/sessionwriter/filepool.go` → `1`. Direct tests: none upstream for this package (grep-pinned only).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "FilePool ensureOpen evictOne sync sessionwriter", limit: 10 });
```

## Verdict
Adopt LRU-fd-pool + empty-file header semantics. Adapt batch/sync worker counts. Omit mobile split-file variant unless porting mob sessions.
