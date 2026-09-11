<!-- capsule-v2 -->
# importer-session-lifecycle — How does the singleton bulk importer serialize sessions, batch commits, and stops?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What state machine turns an uploaded CSV into committed subscribers?

## none→importing→(stopping)→finished|failed over a channel-fed tx batcher
**Path/Symbol:** `internal/subimporter/importer.go` — statuses (:30-38), `NewSession` (:168-196), producer `LoadCSV` (:456-589), consumer `Session.Start` (:274-364), cooperative stop `Importer.Stop` (:592-601) + reader-side check (:519-526), ZIP handling `ExtractZIP` (:374-432).
**Signature:** `commitBatchSize = 10000`; `subQueue chan SubReq` (buffered commitBatchSize); `stop chan bool` (cap 1).
**Data Shape:** Importer is a STATEFUL SINGLETON (one import at a time); SessionOpt carries mode subscribe|blocklist, overwrite flags, delim, list IDs.

### Decisive source
```go
for sub := range s.subQueue {
	if cur == 0 { tx, err = s.im.db.Begin(); ... stmt = tx.Stmt(s.im.opt.UpsertStmt) }
	... stmt.Exec(...)
	cur++; total++
	if cur%commitBatchSize == 0 { tx.Commit() ...; s.im.incrementImportCount(cur); cur = 0 }
}
// queue closed:
if cur == 0 { setStatus(finished); UpdateListDateStmt.Exec(...); sendNotif(finished); return }
tx.Commit(); incrementImportCount(cur); setStatus(finished); ...
```

**Flow:** NewSession rejects when status ∈ {importing, stopping} → LoadCSV counts lines (progress %), maps headers (ASCII-cleaned, email REQUIRED), streams rows: stop-signal select each iteration, ErrFieldCount lines SKIPPED not fatal, bad attribute JSON skipped, validated subs pushed into subQueue → Start() consumes into per-10000 transactions, rolling back the WHOLE current batch only on exec error (fatal) → drain tail commits, list updated_at touched, admin notification fires. Stop() is non-blocking send on cap-1 channel → reader flips to stopping and closes its own queue (producer owns close). ExtractZIP sanitizes entries via filepath.Base (ZIP-slip guard), caps CSV count, marks failed on early return via named `failed` defer flag.
**Invariant:** Status transitions live ONLY on the Importer (mutex-guarded); sessions are disposable workers. Batch-boundary accounting means imported-count lags in multiples of 10000 until final flush — progress math must use total vs imported accordingly. A mid-batch crash loses at most one uncommitted batch by design.
**Probe:** `bash -c "cd <repo> && grep -cF 'commitBatchSize = 10000' internal/subimporter/importer.go"` → 1; `grep -n 'case <-s.im.stop:' internal/subimporter/importer.go` → :521; `grep -cF 'filepath.Base(fName)' internal/subimporter/importer.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "Importer LoadCSV commitBatchSize", limit: 10 });
```
## Verdict
Adopt singleton-state + disposable-session split for long-running uploads; batch-commit with skip-not-fatal row policy. Adapt prepared-statement reuse to your driver. Omit ZIP handling if you accept only direct CSVs.
