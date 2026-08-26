<!-- capsule-v2 -->
# WAL commit publication — who is allowed to make written frames visible, and when?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I separate optimistic private cursors from globally visible publication so no reader ever sees bytes that are not on disk?

## prepare → durable write → publish (the I/O callback publishes, never the submitter)
**Path/Symbol:** `core/storage/wal.rs` three-phase commit (:4790-4930), `commit_prepared_frames` (:4467; legacy cite :4935-4955), spill path `append_frames_vectored` (safety doc :4960-4965, non-durable cursor :5090-5115).
**Signature:** (1) `prepare_frames` serializes pages and computes checksums WITHOUT touching shared WAL state (:708); (2) the caller writes and fsyncs; (3) `commit_prepared_frames` advances max_frame/last_checksum and populates page→frame cache entries — which is what makes frames VISIBLE.
**Data Shape:** prepared frames carry their own checksums; shared state (max_frame, last_checksum, frame cache) mutates only in phase 3.

### Decisive source
```text
// wal.rs:~5060-5085:
// "populating it here -- from the write completion callback -- is what
//  publishes the frames. Doing it before durability would let a reader or a
//  checkpoint pick up a frame whose bytes are not on disk yet."
```

The spill path differs on purpose: `append_frames_vectored` appends optimistically for cacheflush, and its safety doc warns it "should only be used for cacheflush/spilling — the commit path should use prepare_frames + commit_prepared_frames instead." Its optimistic cursor advance is explicitly non-durable bookkeeping: "if the write fails the transaction unwinds and rollback() restores max_frame / last_checksum." One assert guards the local-vs-authority chain branch (:4840-4870): "connection WAL position must not be behind the committed high-water mark." Blocking inside spill is forbidden: "Must NOT block for durability here… A synchronous drain would deadlock a caller that drives I/O from a single-threaded event loop."

**Flow:** prepare (pure) → pwrite+fsync → completion callback populates visibility → readers/checkpointers may consume.
**Invariant:** visibility is granted in exactly one place — the I/O completion callback — and only after durability.
**Probe:** wal.rs:~6415-6450 — after a spill append, `get_max_frame()==1` while shared-visible `get_max_frame_in_wal()==0`, and the next prepare assigns frame_id 2; failure injection at ~6640 asserts a failed prepare leaves max_frame==0 and `find_frame(43)==None`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "prepare_frames commit_prepared_frames append_frames_vectored", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-cursor design (optimistic private + published global) with callback-side publication verbatim; adapt vectored-write batching to your IO backend; omit the authority-chain branch unless you run multi-process. Coverage caveat: none material.
