<!-- capsule-v2 -->
# Logical log streaming reader — how do you parse frames across async IO yields without losing position?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How does a resumable frame parser checkpoint progress so a yield never corrupts the CRC chain or the valid-prefix boundary?

## Re-entrant phase machine with anchor checkpoints
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:StreamingLogicalLogReader.parse_next_transaction` (:2601-2734), phase machinery (:1514, :1638-1714), commit/invalidate (:2964-3001).
**Signature:** phases Header → (ExtensionBlock) → Payload → Trailer; each fully-consumed-and-CRC-folded unit calls `advance_checkpoint`, moving `frame_anchor` to the consume cursor; re-entry rewinds `buffer_offset` to `frame_anchor` and re-runs only the in-flight unit from local state.
**Data Shape:** `frame_in_progress` carries header fields + running_crc across yields; `frame_start` is captured ONCE at frame open ("never recomputed") so an invalid frame reports the correct `last_valid_offset`; `last_valid_offset` is what recovery restores the writer to.

### Decisive source
```text
// logical_log.rs:2590-2600 — doc verbatim:
// "Progress is carried in self.frame_in_progress across IO yields. Each phase
//  … is a re-entrant unit: once fully consumed and folded into the chained CRC
//  it checkpoints (advance_checkpoint) … so read_more_data can compact
//  everything before it and a later yield rewinds only to the latest
//  checkpoint."
```

Outcomes: structurally-complete-but-CRC-failing frame ⇒ `invalidate_frame()` sets `last_valid_offset = frame_start` (:2982); clean trailer ⇒ `commit_frame()` advances it to end-of-frame (:2992); EOF mid-frame ⇒ `abort_frame_eof()` treats the tail as absent. Chained CRC means one corrupted byte kills every LATER frame — by design.

**Flow:** open frame (capture start) → parse/validate per phase → checkpoint after each fold → trailer match ⇒ committed; any mismatch ⇒ tail invalidated at captured start.
**Invariant:** never advance the valid boundary past an unverified byte; on re-entry, re-run at most the current phase — replaying folded bytes would double-fold the CRC.
**Probe:** `test_chained…` family: `test_truncate_retained_when_uncheckpointed_frames_remain` and `test_crc_chain_invalidates_suffix_on_corruption` (logical_log.rs ~5960-6060): corrupting one payload byte in frame 1 of 3 yields InvalidFrame and `last_valid_offset <= after_first`; splice test (`test_splice_frame_from_different_log_rejected`, ~6120+) proves cross-log frame transplant fails via differing salts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "StreamingLogicalLogReader parse_next_transaction frame_anchor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the checkpoint-per-phase parser shape for any resumable binary reader over a checksummed journal; adapt phase set to your format; omit extension-block handling if you have no portable-metadata lane. Coverage caveat: none material — probes are direct in-file tests.
