<!-- capsule-v2 -->
# wc fast paths — stat-then-splice byte counting and SIMD policy gating

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** How does `wc -c` avoid reading bytes, and when is SIMD counting disallowed?

## count_bytes_fast ladder
**Path/Symbol:** `crates/pi-builtins/src/wc.rs:` `count_bytes_using_splice` (:40-64), `count_bytes_fast` (:76-139), `count_bytes_chars_and_lines_fast` (:164+, `AlignedBuffer` :145), `wc_simd_allowed` (:1407-1413).
**Signature:** `fn count_bytes_fast<T: WordCountable>(handle: &mut T) -> (usize, Option<io::Error>)`; const-generic counter `COUNT_BYTES/COUNT_CHARS/COUNT_LINES`.
**Data Shape:** Regular-file path: fstat S_IFREG → remaining = size − lseek(SEEK_CUR); page-size guard: if size NOT a multiple of page size, seek-to-END shortcut is taken (files can grow mid-count; a growing tail would be missed by pure stat). FIFO path (linux): splice input→oversized pipe→/dev/null counting moved bytes; MAX_ROOTLESS_PIPE_SIZE attempts setpipe_size first.

### Decisive source
```rust
if !(stat.st_size as usize).is_multiple_of(sys_page_size) {
	if unsafe { libc::lseek(fd.as_raw_fd(), 0, libc::SEEK_END) } >= 0 {
		return (remaining, None);
	}
}
```
```rust
pub(crate) fn wc_simd_allowed(policy: &SimdPolicy) -> bool {
	let disabled_features = policy.disabled_features();
	if disabled_features.into_iter().any(is_simd_runtime_feature) { return false; }
	policy.iter_features().any(is_simd_runtime_feature)
}
```

**Flow:** bytes-only mode → fast ladder (stat file / splice fifo / plain read fallback) → else buffered loop with 32-byte-aligned buffer feeding bytecount SIMD (`num_chars`, `count '\n'`) with naive fallback when policy denies.
**Invariant:** (1) The page-multiple check encodes "regular files may be concurrently appended" — an exact multiple might be complete OR still growing. (2) Splice failure returns PARTIAL count so the caller falls back to read-loop accounting from there, never double counts. (3) Any explicitly-disabled runtime feature kills SIMD entirely even if others are enabled; `--debug` prints enabled/disabled feature tables.
**Probe:** deterministic anchors: `grep -c 'fn count_bytes_using_splice' crates/pi-builtins/src/wc.rs` = 1; `grep -c 'fn wc_simd_allowed' crates/pi-builtins/src/wc.rs` = 1; test module at wc.rs:1561 pins format/width behavior (runner blocked in this environment — see leaf Provenance).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "wc count bytes fast aligned buffer", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps at pin (`count_bytes_using_splice` wc.rs:40).

## Verdict
Adopt the stat/splice/fallback ladder with its partial-count handoff for any bytes-only counter. Adapt SimdPolicy to your CPU-feature detection; keep the page-multiple growth guard and the all-or-nothing SIMD gate.
