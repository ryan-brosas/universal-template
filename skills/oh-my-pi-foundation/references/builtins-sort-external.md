<!-- capsule-v2 -->
# sort external merge — two-thread chunk pipeline, compressor probe, sorter-panic surfacing

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils coreutils 0.8.0 port); Codebase Memory `oh-my-pi`. **Question:** How does sort handle inputs larger than memory, and how does a panic inside the sorter thread avoid masquerading as success?

## ext_sort reader/sorter channels
**Path/Symbol:** `crates/pi-builtins/src/sort.rs:` `mod threaded` doc :905-918, `ext_sort` (:952-1030), `sorter` (:1111-1125), buffer sizing (:1045-1054), `sort_by` parallel choice (:5022-5047), spill test `ext_sort_spills_to_files_and_sorts` (:1245).
**Signature:** `pub fn ext_sort(files, settings, output, tmp_dir: &mut TmpDirWrapper, stderr: OpenFile) -> SortResult<()>`; channels `flume::bounded(1)` for sorted chunks and recycled buffers.
**Data Shape:** Default read buffer 8 KiB (`DEFAULT_BUF_SIZE`, pinned by test note); auto (non-explicit) buffer sizes clamp to ≥8 MiB; explicit requests >512 MiB halved. Chunk recycling via second bounded channel.

### Decisive source
```rust
// Surface a sorter-thread panic ... as an error. `chunks::read` now reports the
// sorter's disconnection as end-of-input (issue #6736), so without joining here a
// discarded panic would MASQUERADE AS A SUCCESSFUL SHORT READ and let `sort`
// exit 0 with truncated or empty output.
drop(sorted_receiver);                       // unblock a pending send after I/O error
match sorter_handle.join() {
	Ok(()) => result,
	Err(_) => result.and(Err(SortError::message("sort: sorter thread terminated unexpectedly"))),
}
```

**Flow:** probe `--compress-program` FIRST by spawning it with null stdio — resolved via ChildEnv (shell PATH/cwd), kill immediately on success, disable-with-warning on failure (a compressor installed only for the shell must not be rejected) → reader thread accumulates chunks, spills sorted chunks to temp files (plain or compressed variant chosen by probe outcome) → sorter thread sorts each chunk (rayon par_sort when pool available AND not stable/unique; stable/unique forces stable sort) → merge_with_file_limit reopens closed temp files → output.
**Invariant:** (1) Join before returning or a comparator/rayon panic becomes silent truncation. (2) Drop the receiver BEFORE join so an erroring reader never deadlocks the sorter's send. (3) `par_sort_unstable_by` only when neither --stable nor --unique; WASI always sequential. (4) Comparator fast paths: whole-line lexicographic, precomputed locale collation keys, ASCII-insensitive — checked in that order before per-selector comparison; float compare uses partial_cmp NOT total_cmp because total_cmp orders -0 before 0.
**Probe:** direct test `sort.rs:1245 ext_sort_spills_to_files_and_sorts` (200 reverse-ordered zero-padded numbers, buffer_size 64, asserts byte-exact sorted output). Deterministic anchors: `grep -c 'sorter thread terminated unexpectedly' crates/pi-builtins/src/sort.rs` = 1; `grep -c 'DEFAULT_BUF_SIZE' crates/pi-builtins/src/sort.rs` ≥ 3.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ext_sort sorter thread terminated unexpectedly", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `sort.sorter sort.rs:1111-1125`.

## Verdict
Adopt the bounded-channel chunk/recycle pipeline + join-before-return panic rule + shell-PATH compressor probe for any external sort. Adapt flume→your mpsc; keep buffer-size clamps and the stable/unique ⇒ no-rayon rule. Omit WASI fallbacks unless targeting it.
