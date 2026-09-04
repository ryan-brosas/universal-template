<!-- capsule-v2 -->
# SpinLock — when is a bare test-and-spin lock the right primitive, and what must it never grow?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What does a minimal, correct spin lock look like in an async storage engine, and where are its honest limits?

## AtomicBool swap-acquire + Release-on-drop guard; no fairness, no poisoning
**Path/Symbol:** `core/fast_lock.rs:7-52` (`SpinLock<T>`, `SpinLockGuard`), 1000-thread contention test :55+.
**Signature:** `pub fn lock(&self) -> SpinLockGuard<'_, T>` — `while self.locked.swap(true, Ordering::Acquire) { spin_loop(); }`; guard `Drop` stores false with Release.
**Data Shape:** `locked: AtomicBool` + `UnsafeCell<T>`; Send/Sync impls gated on `T: Send`. No try_lock, no timeout, no owner tracking.

### Decisive source
```rust
// :33-40 — complete acquire/release:
pub fn lock(&self) -> SpinLockGuard<'_, T> {
    while self.locked.swap(true, Ordering::Acquire) {
        spin_loop();
    }
    SpinLockGuard { lock: self }
}
impl<T> Drop for SpinLockGuard<'_, T> {
    fn drop(&mut self) { self.lock.locked.store(false, Ordering::Release); }
}
```
The Acquire/Release pair is exactly what a mutex needs: acquiring synchronizes with the previous holder's releases. Where it's used matters more than the code: short, non-blocking critical sections (MVCC per-tx bookkeeping) — and critically NOT around I/O; every long or yielding path in turso uses state machines + TursoRwLock instead. The engine's own commit-state docs say an async transformation would remove the explicit mutex (mod.rs:1464-1466 TODO), confirming these locks are stopgaps for CPU-only sections.

**Flow:** swap(true) wins → guard lives → deref through UnsafeCell → drop stores false → next waiter's swap fails-through.
**Invariant:** hold times bounded by CPU work only; guard-based release makes early-return/panic paths safe without poison semantics; never await/yield while holding.
**Probe:** `test_fast_lock_multiple_thread_sum` (:55+) — 1000 threads incrementing through the guard asserts linearizability under contention.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "SpinLock SpinLockGuard fast_lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for sub-microsecond CPU-only sections beside async machinery. Adapt to your spin-loop hint. Omit everywhere else — adding fairness/poisoning here just rebuilds std::sync::Mutex badly.
