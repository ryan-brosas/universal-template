<!-- capsule-v2 -->
# Pluggable IO/VFS abstraction — what contract must every storage backend satisfy?

**Source:** turso (MIT) `main@def9a0601b8e` (/mnt/hdd/utopia/inspo/memory/turso); Codebase Memory project `turso`. **Question:** Which traits define the engine's IO boundary, and what default-method plumbing can a porter reuse instead of rewriting?

## One IO trait, one File trait, many backends
**Path/Symbol:** `core/io/mod.rs`: trait `IO: Clock + Send + Sync` (:424-470+), trait `File` (:153-260+), `FileId` (:57-64), cfg_block platform selection (:21-51); `core/io/vfs.rs` (extension-VFS bridge); backends `unix.rs`, `io_uring.rs`, `windows.rs`, `win_iocp.rs`, `memory.rs`, `generic.rs`, `vfs.rs`.
**Signature:** `fn open_file(&self, path: &str, flags: OpenFlags, direct: bool) -> Result<Arc<dyn File>>`; `File::{pread(pos, c) -> Result<Completion>, pwrite(pos, Arc<Buffer>, c), sync(c, FileSyncType), size(), truncate(len, c), lock_file(exclusive), pwritev(buffers, c)}`; `IO::{step() -> Result<()>, cancel(&[Completion]), drain_completions(&[Completion]), wait_for_completion(c), supports_shared_wal_coordination() -> bool}`.
**Data Shape:** backends are selected at compile time by cfg_block (io_uring behind feature flag, UnixIO as PlatformIO/SyscallIO on unix, WindowsIO on windows, GenericIO fallback, miri forces generic); `FileId { dev, ino }` identifies files across platforms with synthetic hash identity for non-FS backends (MemoryIO, OPFS, simulators).

### Decisive source
```rust
// mod.rs:160-193 — pwritev DEFAULT implementation composes N pwrites into one
// logical completion: per-child AtomicUsize outstanding counter, total_written
// accumulation, last finisher completes the parent with the summed byte count,
// c.abort() on ANY child submit failure. Comment: "naive default implementation
// can be overridden on backends where it makes sense to" (io_uring vectorizes).
// mod.rs:443-468 — drain_completions waits ONLY on the caller-passed slice:
//   "Unlike a global 'drain the ring' barrier, this only waits on the
//    completions the caller passes in. Other threads can keep submitting
//    concurrently… Completion::finished() is monotonic (OnceLock-backed), so
//    the loop will terminate."
```

**Flow:** engine code never touches syscalls — it holds `Arc<dyn File>` + the owning `Arc<dyn IO>`; every data-plane call takes a Completion (see io-completions-groups); `step()` pumps the backend; optional capabilities are default-methods returning errors (`shared_wal_lock_byte`) or false (`supports_shared_wal_coordination`) so backends declare support explicitly; `has_hole`/`punch_hole` panic-by-default because only the sync engine uses sparse-file support.
**Invariant:** the blocking boundary is exactly `step()` — no File method ever blocks; synchronous-looking callers wrap it in drain_completions/wait_for_completion loops.
**Probe:** `core/io/memory.rs:283-320` shows the minimal compliant backend (pread/pwrite/pwritev over an in-memory map) used by hundreds of tests; `core/io/vfs.rs:25-50` shows the extension-side adapter translating C-function-pointer VFS modules onto the same traits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "trait IO open_file step UnixIO UringIO MemoryIO", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-trait split (factory+lifecycle on IO, data plane on File) and the default pwritev composition — reusable for any engine needing swappable IO. Adapt platform backend internals freely; they are deliberately isolated. Omit hole-punching unless you port the sync engine. Coverage caveat: io_uring/windows paths are compile-gated and exercised by integration/simulator runs rather than unit probes in-tree.
