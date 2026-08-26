<!-- capsule-v2 -->
# panic containment + crash-hook cooperation — how a utility panic stays out of the crash report

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What coordinates between run_caught's catch_unwind and the native crash hook so caught panics are not reported as crashes?

## PANIC_SCOPE_DEPTH protocol
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` thread_local (:544-551), `panic_scope_active` (:559-561), Guard in `run_caught` (:811-828); exported via lib.rs `pub use host::{panic_scope_active, ...}`.
**Signature:** `pub fn panic_scope_active() -> bool`; Guard::drop saturating-subtracts.
**Data Shape:** `Cell<usize>` NOT RefCell — "the panicking code may hold other borrows, and a RefCell borrow there would panic again and abort the process."

### Decisive source
```rust
/// Depth of active utility bodies on this thread. The native crash hook reads
/// this from inside a panic (see `panic_scope_active`) to decide whether the
/// panic is about to be caught; a `Cell` is used because the panicking code may
/// hold other borrows, and a `RefCell` borrow there would panic again and abort.
static PANIC_SCOPE_DEPTH: Cell<usize> = const { Cell::new(0) };
```
```rust
pub(crate) fn run_caught<U: Utility>(parsed: U, host: &mut Host) -> i32 {
	PANIC_SCOPE_DEPTH.with(|depth| depth.set(depth.get() + 1));
	let _guard = Guard;
	match catch_unwind(AssertUnwindSafe(|| parsed.run(host))) {
		Ok(code) => code,
		Err(_) => { let _ = writeln!(host.stderr, "{}: internal error", U::NAME); 1 },
	}
}
```

**Flow:** increment before body, decrement in Drop (unwind-safe through panics) → the process-wide native crash hook consults `panic_scope_active()` from its panic handler: true ⇒ recoverable (skip crash report) — false ⇒ real crash. Related global: `RAYON_GLOBAL_POOL_AVAILABLE` AtomicBool lets pi-natives disable rayon pool entry after Windows commit-pressure incidents.
**Invariant:** AssertUnwindSafe is required because Utility/Host contain non-UnwindSafe internals — the boundary guarantees no state escapes half-mutated into the shell beyond what Drop cleans. Exit code 1 + `<NAME>: internal error` is the ONLY user-visible trace of a contained panic.
**Probe:** deterministic anchors: `grep -c 'PANIC_SCOPE_DEPTH' crates/pi-builtins/src/host.rs` = 4 (decl, accessor, increment, Guard drop); `grep -c 'fn panic_scope_active' crates/pi-builtins/src/host.rs` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "panic scope active crash hook utility", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (host.rs:550/:559).

## Verdict
Adopt the depth-counter + hook-consultation protocol for any plugin/utility boundary inside a long-lived process with a crash reporter. Adapt the hook to your reporter; never replace the Cell with a RefCell and never skip the Drop guard.
