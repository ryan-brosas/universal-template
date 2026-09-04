<!-- capsule-v2 -->
# Destination-aware stdout buffering — why does live tool output stall until exit if you buffer like a normal CLI?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** When does a utility's output become visible to the pipeline consumer, and how are `2>&1` interleavings kept in exact write order?

## StreamWriter policy
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` `enum StreamWriter` (:305-316), `StreamWriter::new` (:323-325), `fn is_regular_file` (:393-398), `fn same_destination` (:410-425), `Host::stdout_writer` (:223-228), merged-writer construction in `build_host` (:874-879).
**Signature:** `fn new(file: OpenFile) -> Self` (block for regular files, line otherwise); `pub fn stdout_writer(&self) -> StreamWriter`.
**Data Shape:** Three variants: `Block(BufWriter<OpenFile>)` 64 KiB, `Line(LineWriter<OpenFile>)` 16 KiB, `Shared(Arc<Mutex<StreamWriter>>)` for the one-destination case. Capacities are constants on StreamWriter.

### Decisive source
```rust
/// Whether writes to `file` land in a regular file, where output is only ever
/// observed after the utility exits.
pub(crate) fn is_regular_file(file: &OpenFile) -> bool {
	match file {
		OpenFile::File(f) => f.metadata().is_ok_and(|m| m.is_file()),
		_ => false,
	}
}
```

**Flow:** fd1 destination classified by fstat → regular file = block-buffered (nobody observes until exit); everything else — pipes, the TUI capture pipe wrapped as `OpenFile::File` (fifo file type), in-memory streams — line-buffered so each completed line is visible as produced → if fd2 shares fd1's destination (`2>&1`, or the default capture pipe), ONE shared mutexed writer backs both streams.
**Invariant:** (1) The fstat is mandatory: the shell hands commands their stdout as a pipe fd wrapped in `std::fs::File`; matching on enum variants instead would block-buffer it and stall live tool output until exit. (2) `same_destination` matches by device+inode and DELIBERATELY EXCLUDES regular files: under `cmd >f 2>f` two descriptions have independent offsets, so merging writers would change where bytes land; offset-free objects (pipes/fifos/ttys/sockets) with equal dev+ino ARE the same object. (3) `dup_file()` does NOT carry buffered data across (at most one partial line lost) — utilities handing raw handles to helper threads accept this. Explicit `StreamWriter::line/block` force policies for flags like `rg --line-buffered`.
**Probe:** `crates/pi-builtins/src/host.rs:1235` `pipe_wrapped_as_file_gets_line_buffering` + :1266 `same_destination_detects_dup_pipes_only` (asserts dup pipes merge, distinct pipes don't, two opens of one regular file don't) + :1246 `shared_handles_preserve_write_order` (`out err out` interleave byte-exact).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "is_regular_file StreamWriter line buffered", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `host.is_regular_file host.rs:393-398`.

## Verdict
Adopt destination-classified buffering + shared-writer `2>&1` merging for any in-process tool whose consumer streams incrementally. Adapt the OpenFile wrapper to your descriptor type but keep the fstat-not-variant-match rule. Omit Windows stub (`same_destination` returns false).
