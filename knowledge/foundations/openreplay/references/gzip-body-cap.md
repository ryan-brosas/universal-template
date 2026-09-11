<!-- capsule-v2 -->
# Gzip beacon body reader with per-session cap — how is a tracker upload body size-bounded and transparently decompressed?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What reading pattern prevents decompression bombs and oversized beacons on the ingest endpoint?

## MaxBytesReader wraps BEFORE gunzip; Content-Encoding sniff
**Path/Symbol:** `backend/pkg/server/api/request.go` — `ReadCompressedBody` (:81–112); callers `startSessionHandlerWeb` (limit = cfg JsonSizeLimit) and `pushMessagesHandlerWeb` (`handlers.go:344`, limit = per-session BeaconCache value).
**Signature:** `ReadCompressedBody(log, w, r, limit int64) ([]byte, error)`.
**Data Shape:** gzip path streams through `gzip.NewReader(http.MaxBytesReader(w, r.Body, limit))`; plain path same wrapper; error ⇒ caller answers 413.

### Decisive source
```go
body := http.MaxBytesReader(w, r.Body, limit)      // cap applies to COMPRESSED bytes
if r.Header.Get("Content-Encoding") == "gzip" {
    reader, err := gzip.NewReader(body)
    ...
    bodyBytes, err = io.ReadAll(reader)
} else {
    bodyBytes, err = io.ReadAll(body)
}
```

**Flow:** ingest POST → wrap raw body with the session's beacon-size budget → branch on Content-Encoding → read all → close with warn-only error handling → handler proceeds; oversize aborts with StatusRequestEntityTooLarge before JSON/Kafka work.
**Invariant:** The cap must wrap the RAW stream (pre-gunzip), since decompression can amplify bytes ~1000×. Close errors are logged but never mask a successful read.
**Probe:** `grep -c 'MaxBytesReader' backend/pkg/server/api/request.go` → `2`; `grep -c 'ReadCompressedBody' backend/pkg/sessions/api/web/handlers.go` → `2`; direct tests: none upstream for this helper (grep-pinned caveat).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "ReadCompressedBody MaxBytesReader gzip Content-Encoding", limit: 10 });
```

## Verdict
Adopt pre-decompression capping. Adapt limit source. Omit gzip branch if clients never compress.
