<!-- capsule-v2 -->
# Commit-log rotation — never reuse a file, open-before-close, name derived from the old name

**Source:** Weaviate BSD-3-Clause `main@adcffc5432aa797c60e3c4e479514054254fae2a`; Codebase Memory `ext-weaviate`. **Question:** How does the HNSW WAL rotate at 100MB without corrupting snapshots or losing writes on failure?

## Fresh-file startup + failure-safe switch
**Path/Symbol:** `adapters/repos/db/vector/hnsw/commit_logger.go:33` (`defaultCommitLogSize = 500MB`, per-file max = size/5), `:89-116` (fresh-file startup), `:138-246` (`createNewCommitFile`/`pruneEmptyRawCommitLogs`), `:503-618` (`switchCommitLogs`/`nextCommitLogFileName`).
**Signature:** `switchCommitLogs(force bool) (bool, error)`; `nextCommitLogFileName(current string) (name string, derived bool)`.
**Data Shape:** directory `<rootPath>/<id>.hnsw.commitlog.d/`; raw files named by unix-second; derived artifacts carry `.snapshot`/`.sorted`/`.condensed` suffixes or `_` range separators; 32KB bufio writer wrapped by compact.WALWriter.

### Decisive source
```go
// startup: ALWAYS create a fresh raw file. Reusing an existing file is a footgun:
// getCurrentCommitLogFileName used to select the append target by highest parsed
// timestamp, which let it hand back a .snapshot/.sorted/.condensed file and the
// next AddNode would corrupt it (block CRCs become invalid on next load).
// Zero-byte raw files from previous startups are pruned first.
// rotation:
if err := oldWriter.Flush(); err != nil { return true, errors.Wrap(err, "flush commit log") }
if err := oldFile.Sync(); err != nil   { return true, ... }        // durable BEFORE stop appending
fileName, _ := nextCommitLogFileName(info.Name())                  // derived from OLD name, not clock
fd, err := l.fs.OpenFile(filePath, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0o666)
if err != nil { return true, ... }                                  // old fd still live ⇒ retry next cycle
l.currentFile = fd; l.currentWriter = bufio.NewWriterSize(fd, 32*1024)
l.walWriter = compact.NewWALWriter(l.currentWriter)                 // redirect BEFORE touching old fd
... oldFile.Close() // cleanup only; failure = leaked fd, never lost writes
// nextCommitLogFileName: now > ts ⇒ now; else ts+1  (two switches in one second must not collide)
```

**Flow:** every startup creates a brand-new raw file (append path can only ever land on a fresh owned file); empty leftovers pruned best-effort. Rotation on size > maxSizeIndividual (100MB): flush+fsync old → derive new name (old-timestamp+1 if same second — burst-safe for concurrent backups) → open new BEFORE closing old so any failure leaves currentFile pointing at a healthy fd and writes continue unrotated → swap pointer → close old as mere cleanup. `ActiveFilePath()` lets backups exclude the active file by identity, not by size==0 heuristics.
**Invariant:** The old file must NOT be closed until the new one is successfully opened (comment :522-526) — closing first turns an ENOSPC into writes-to-a-closed-fd. Name derivation from the clock alone reopens the just-rotated-out file inside one second (TestSwitchCommitLogsBurst). Per-batch Flush() deliberately skips fsync (import-regression #199, ~15-30% on slow disks): durability comes from rebuild-from-object-store, not WAL fsync.
**Probe:** direct tests pin every clause: `commit_logger_rotation_test.go::TestCommitLogRotation_{NewFileOpenFails,CloseFails,SyncFails}_KeepsWriting` (:91/:108/:122), `commit_logger_snapshot_collision_regression_test.go::TestCommitLogger_NeverAppendsToSnapshot/_NeverAppendsToNonRaw_AllSuffixes/_PrunesEmptyRawFiles` (:48/:103/:143), `commit_logger_switch_naming_test.go::TestNextCommitLogFileName/TestSwitchCommitLogsBurst` (:27/:72).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-weaviate", query: "commit logger switchCommitLogs rotation WAL writer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fresh-file startup, open-before-close rotation, old-name-derived naming, and fsync-only-on-rotation. Adapt sizes (500MB default / 100MB per-file) as tunables. Omit metered IO wrappers.
