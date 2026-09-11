<!-- capsule-v2 -->
# diff-stream-native-diff — what does the native streaming differ guarantee while ingestion is still running, and why is that the only thing a live UI may show?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** You want to render a split diff WHILE both sides are still downloading. Which lines are provably stable at that moment?

## DiffStream / DiffStreamState
**Path/Symbol:** `crates/pi-natives/src/diff.rs` (`DiffStream`, `DiffStreamState.update_stable_common`, `StreamSide`).
**Signature:** `push(side, chunk: string)` / `push_bytes(side, chunk: Uint8Array) -> DiffStreamProgress`; `finish_side(side)`; `mark_too_large(side)`; `lines(side, from, limit?)`; `finish(context?) -> Promise<DiffStreamResult>`.
**Data Shape:** `DiffStreamProgress { old_lines, new_lines, stable_common_lines, old_done, new_done, binary, too_large }` — line counts and stability counters over UTF-16 stored text; sides carry `pending_utf8` for chunk-boundary decoding.

### Decisive source
```rust
fn update_stable_common(&mut self) {
	let available = self.old.line_ends.len().min(self.new.line_ends.len());
	while self.stable_common < available
		&& self.old.line(self.stable_common) == self.new.line(self.stable_common)
	{
		self.stable_common += 1;
	}
}
```

**Flow:** Every mutation (`push`, `push_bytes`, `finish_side`, `mark_too_large`, worker file reads) re-runs `update_stable_common`, which extends ONLY the equal leading-line prefix. `lines()` exposes complete lines by index (newline terminator stripped in `display_line`); `finish()` refuses until BOTH sides are done (`"Both diff sides must finish before computing the result"`), then clones both texts and computes exact Myers runs + unified hunks on the blocking pool. Pushing to a finished side errors ("Cannot push to a finished diff side"); pushing during an active native file read errors too.
**Invariant:** Only equal COMPLETE leading lines are declared stable — after the first mismatched pair, later identical lines must NOT be shown as aligned because Myers can still realign them once either side finishes; a monotonic counter means it never regresses.
**Probe:** `grep -nF 'fn update_stable_common(&mut self)' crates/pi-natives/src/diff.rs` → line `563` and `grep -nF 'Both diff sides must finish' crates/pi-natives/src/diff.rs` → line `719`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "DiffStream update_stable_common stable_common_lines finish Myers worker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stable-prefix rule verbatim (it is what makes provisional rendering honest); adapt the napi/threading shell to your FFI; omit the utf8 replacement-char tail policy only if your chunks are always valid UTF-8. Direct test: Rust unit tests in `diff.rs` (`stream_progress_exposes_only_stable_complete_prefix`) plus the TS consumer battery in `packages/natives/test/diff.test.ts`.
