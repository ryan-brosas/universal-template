<!-- capsule-v2 -->
# Native DiffStream — how do you diff two files that are still being read, exposing complete lines live and an exact Myers result only at EOF?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What does the incremental two-sided ingestion contract guarantee DURING streaming versus only after `finish()`, and what is the exact line-completeness rule?

## Stream-side invariants
**Path/Symbol:** `crates/pi-natives/src/diff.rs:` `DiffStreamProgress` (:88–103), `StreamSide::append_units` (:434–443), `append_utf8` (:474–509), `finish` (:511–523), `line`/`display_line` (:525–538), `update_stable_common` (:563–570), `DiffStream::{push, push_bytes, finish_side, mark_too_large, lines, text}` (:607–672), `open_file` (:680–712), `read_file_into_stream` (:728–773).
**Signature:** `push(side, chunk: JsString) -> DiffStreamProgress; push_bytes(side, chunk: Uint8Array) -> …; finish_side(side) -> …; finish(context: Option<u32>) -> Promise<DiffStreamResult>`; state under one `Arc<Mutex<…>>`.
**Data Shape:** Progress `{old_lines, new_lines, stable_common_lines, old_done, new_done, binary, too_large}` — binary = NUL byte/code unit on EITHER side; text kept as UTF-16 with a `line_ends` offset vector.

### Decisive source
```rust
fn append_utf8(&mut self, bytes: &[u8], final_chunk: bool) {
	self.binary |= bytes.contains(&0);
	self.pending_utf8.extend_from_slice(bytes);
	// decode valid prefixes; invalid complete sequences → U+FFFD;
	// incomplete tail stays pending until more bytes or final_chunk:
	if final_chunk && offset < self.pending_utf8.len() { decoded.push(REPLACEMENT_CHARACTER as u16); }
	...
}
fn finish(&mut self) {
	if !self.text.is_empty() && self.text.last() != Some(&LF) {
		self.line_ends.push(self.text.len());      // unterminated last line becomes visible ONLY here
	}
	self.done = true;
}
```

**Flow:** chunks land on one side → every LF records a `line_ends` boundary so complete lines are queryable immediately via `lines(side, from, limit)` (newline terminator stripped by `display_line`) → `update_stable_common` walks the leading prefix where old/new line slices are byte-equal and advances a monotonic cursor → when BOTH sides are done, `finish()` computes exact Myers runs + unified hunks on the blocking pool (`task::blocking("diff.finish")`) from full-text snapshots. `open_file` reads on the native pool in 64 KiB chunks (`vec![0u8; 64 * 1024]`, :753) with `cancel.heartbeat()?` per iteration, stopping early on binary detection or pre-size over `max_bytes`; JS polls progress/lines while the promise is pending.
**Invariant:** The doc-comment IS the contract (:585–590): "Complete lines are observable during ingestion. Only equal leading lines are declared stable before EOF; future input can change Myers alignment after the first mismatch." So renderers may paint `stable_common_lines` confidently but must NOT lay out hunks until both sides report done. State-machine guards: pushing to a done side errors; pushing while a native read is active errors; `finish_side` refuses during active reads; `mark_too_large` completes without further ingestion. Streamed result ≡ synchronous `structured_patch_hunks` (test-pinned equality incl. `\ No newline at end of file` markers and CRLF cases).
**Probe:** `packages/natives/test/diff.test.ts` — `"streamed chunks produce the exact complete-file hunks"` pins split-chunk equality + `stableCommonLines === 1` after the first four pushes (:152); `"native file open streams complete lines without a JS file read"` pins `openFile` → `{newDone:true, newLines:2}` + `lines(DiffSide.New,0)` = `["first","second"]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "DiffStream push_bytes open_file stable_common", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `push_bytes diff.rs:616-621`, `open_file :680-712`, `update_stable_common :563-570`.

## Verdict
Adopt incremental side-ingestion with a conservative stable-prefix for any progressive-diff UI; adapt storage to your string model but keep UTF-8-boundary-safe decoding (never split a code point mid-chunk). Omit the napi/task plumbing if your host threads differently — but keep the Myers computation OFF the UI thread. Runner caveat: cargo nightly pinned (`rust-toolchain.toml` nightly-2026-08-08) — Rust tests not runnable in this environment.
