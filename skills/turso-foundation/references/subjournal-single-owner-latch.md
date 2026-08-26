<!-- capsule-v2 -->
# Subjournal single-owner latch — who may write statement-level before-images when multiple statements share one connection-scoped pager?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you gate a shared rollback journal so exactly one statement owns it, and what wire format must its records carry for restore to work?

## CAS-latch ownership + page_size+4 record format
**Path/Symbol:** `core/storage/subjournal.rs:12-135` (`struct Subjournal`, whole file), pager integration `core/storage/pager.rs:1874-1994` (`open_subjournal` :1879, `subjournal_page_if_required` :1898, `try_use_subjournal` :1974, `stop_use_subjournal` :1982), savepoint bookkeeping struct `Savepoint` (`pager.rs:1260-1297`: `start_offset`/`write_offset` AtomicU64, `page_bitmap` RoaringBitmap, `db_size` AtomicU32).
**Signature:** `fn try_use(&self) -> Result<()>` — `in_use.compare_exchange(false, true, SeqCst, SeqCst)`, failure ⇒ `Err(LimboError::Busy)` (caller retries later); `fn stop_use(&self)` — reverse CAS behind `turso_assert!(result.is_ok(), "try_start_use must succeed before stop_use call")`.
**Data Shape:** each record is ONE buffer of `page_size + 4` bytes: `[u32 BE page id][raw page image]` — the id prefix lets restore walk the journal without a side index. Writers assert both lengths (`turso_assert_eq!(buffer.len(), page_size + 4, ...)` subjournal.rs:56-60).

### Decisive source
```rust
// pager.rs:1905-1912 — which pages get journaled at all:
// Skip subjournaling for pages that didn't exist when the savepoint was opened.
// New pages (allocated during this statement) can be "rolled back" by simply
// truncating back to the original db_size. This matches SQLite's subjRequiresPage()
// which checks: p->nOrig >= pgno.
let page_id_u32 = page.get().id as u32;
if page_id_u32 > cur_savepoint.db_size.load(Ordering::Acquire) { return Ok(()); }
if cur_savepoint.has_dirty_page(page_id_u32) { return Ok(()); } // first-image-wins
```
The dirty-bitmap check makes the FIRST before-image per page authoritative: later writes to the same page within one savepoint are skipped because rollback only needs the original image. The offset advance happens in the WRITE COMPLETION callback (:1966-1971): `add_dirty_page(page_id)` then `write_offset.fetch_add(page_size + 4, SeqCst)` — the offset never moves ahead of confirmed bytes.

**Flow:** statement start ⇒ `try_use_subjournal()` (Busy ⇒ retry) → per first-dirty-page: build id+image buffer under savepoint lock (capturing write_offset BEFORE the async pwrite) → pwrite → completion advances write_offset + marks bitmap → statement end ⇒ `stop_use_subjournal()` (only ever after successful try_use — enforced by assert). Rollback = truncate to savepoint `start_offset` + restore images by page id.
**Invariant:** ownership latch is all-or-nothing (no readers-vs-writer split); a page's journaled image must be its PRE-savepoint content (first-image-wins), and every byte counted in `write_offset` must already be durably written — advancing early would let a rollback truncate past real data.
**Probe:** fuzz suite `tests/fuzz/subjournal.rs` (`subjournal_differential_fuzz` :469, `subjournal_replace_abort_fallback` :772, `subjournal_update_replace_fuzz` :895, `subjournal_delete_fk_fuzz` :1021) drives savepoint open/write/rollback against differential oracles; VDBE call sites `core/vdbe/execute.rs:4500-4503` and `core/vdbe/mod.rs:1250-1253,1388,1392,2927` show the try/stop pairing incl. error paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "Subjournal try_use stop_use subjournal_page_if_required", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the CAS single-owner latch + first-image-wins before-images for any shared statement-scoped undo log; adopt the id-prefixed record format whenever restore must be self-describing. Adapt Busy handling to your scheduler (async retry vs thread yield). Omit the RoaringBitmap if your workload keeps savepoints tiny — but keep SOME per-savepoint dirty set, or you re-journal hot pages on every statement.
