<!-- capsule-v2 -->
# Stdin cancellation polling — how does a blocked pipe read return EOF on abort?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Why can't the utility just block on read, and what exact loop makes abort/timeout responsive?

## Stdin Read impl
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` `struct Stdin` (:492-497), `impl Read for Stdin` (:513-541), fd capture in build_host (:836-846), comment :90-93.
**Signature:** `fn read(&mut self, buf: &mut [u8]) -> io::Result<usize>` — returns Ok(0) (EOF) when cancelled.
**Data Shape:** unix: raw fd captured via try_borrow_as_fd BEFORE moving OpenFile to the struct (kept alive by it); poll(200 ms) slices; EINTR retries; non-unix/no-fd falls through to a plain blocking read with only the pre-read flag check.

### Decisive source
```rust
#[cfg(unix)]
if let Some(fd) = self.fd {
	loop {
		if self.cancel.load(Ordering::Relaxed) { return Ok(0); }
		let mut pfd = libc::pollfd { fd, events: libc::POLLIN, revents: 0 };
		let ready = unsafe { libc::poll(&mut pfd, 1, 200) };
		if ready < 0 {
			let err = io::Error::last_os_error();
			if err.kind() == io::ErrorKind::Interrupted { continue; }
			return Err(err);
		}
		if ready > 0 { break; }   // data ready -> fall through to real read
	}
}
self.file.read(buf)
```

**Flow:** adapter select: cancel-token fires ⇒ set shared cancel flag → the blocked read's NEXT 200 ms poll slice observes it → returns EOF → utility sees end-of-input, unwinds cleanly flushing partial output → blocking task completes; adapter AWAITS completion before returning so no detached thread keeps writing to moved descriptors.
**Invariant:** (1) The utility must treat EOF-on-cancel as normal termination — output produced so far is kept ("flushing what it already produced"). (2) Final exit code is forced to 130 by the adapter when the token fired regardless of what the body returned. (3) The fd borrow happens while the ExecutionContext is alive; the OwnedFd clone keeps the number valid for the task's lifetime. (4) CancelOnDrop sets the flag if the adapter future itself is dropped mid-await.
**Probe:** deterministic anchors: `grep -c 'libc::poll' crates/pi-builtins/src/host.rs` ≥ 1; contract tests host.rs:1197/:1216 pin the flush side; cancellation side pinned by adapter comments + `CancelOnDrop` (:114-120).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "stdin poll cancellation eof blocked pipe", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (host.rs:524).

## Verdict
Adopt sliced-poll stdin wrapping for every cancellable consumer inside an async runtime — plain spawn_blocking reads make timeout unenforceable. Adapt poll to your IO library; keep EOF-means-cancel semantics and the await-completion-before-return rule.
