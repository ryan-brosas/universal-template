<!-- capsule-v2 -->
# Fork-vs-setter cancellation ladder — how a server writes its database while readers hold clones, without deadlocking

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** When one thread must mutate the canonical database (salsa setters require exclusive access) while other threads hold clones, how do you coordinate so no reader or writer ever waits forever?

## OwnedDb fork/setter choreography
**Path/Symbol:** `crates/biome_service/src/db/state.rs:287-297` (`OwnedDb`), `:309-326` (`fork` loop), `:328-351` (`with_setter`).
**Signature:** `fn fork(&self) -> WorkspaceDb`; `fn with_setter<R>(&self, f: impl FnOnce(&mut WorkspaceDb) -> R) -> R`; state: `db: Mutex<WorkspaceDb>`, `pending_setters: AtomicUsize`.
**Data Shape:** `pending_setters > 0` means some thread waits for ALL clones to drop; salsa setters can only run once every clone is gone.

### Decisive source
```rust
// :309-325 — never block: unwind instead of queueing behind a setter
fn fork(&self) -> WorkspaceDb {
    loop {
        if self.pending_setters.load(Ordering::Acquire) > 0 {
            resume_unwind(Box::new(salsa::Cancelled::PendingWrite));
        }
        if let Some(db) = self.db.try_lock() {
            return db.clone();
        }
        std::thread::yield_now();
    }
}
// :336-345 — same-thread read-then-write is rejected loudly, not awaited
if LIVE_READS.with(|reads| reads.get()) != 0 {
    debug_assert!(false, "db setter invoked while this thread holds a db clone; ...");
    error!("db setter invoked while this thread holds a db clone; cancelling the update to avoid a deadlock");
    resume_unwind(Box::new(salsa::Cancelled::PendingWrite));
}
self.pending_setters.fetch_add(1, Ordering::Release);
let _guard = PendingSetterGuard(&self.pending_setters); // RAII decrement
let mut db = self.db.lock();
f(&mut db)
```

**Flow:** reader: check `pending_setters` (Acquire) → try-lock (never block; a setter may grab the lock right after the check, hence re-loop with `yield_now`) → clone db. Writer: refuse if THIS thread holds a live fork (debug_assert + unwind) → bump `pending_setters` (Release) under RAII guard → take the mutex for the whole setter.
**Invariant:** No lock acquisition in `fork` may wait on the setter mutex — waiting there could deadlock against a clone the calling thread already holds. Cancellation (`salsa::Cancelled::PendingWrite` unwound through `resume_unwind`) is the liveness mechanism; frameworks that call into user code catch it and retry. Cross-thread readers that started before the setter simply finish their clones; NEW forks unwind and retry at a higher level.
**Probe:** `grep -c 'resume_unwind(Box::new(salsa::Cancelled::PendingWrite))' crates/biome_service/src/db/state.rs` → `2` (:315 fork path, :344 setter path); `grep -n 'std::thread::yield_now' crates/biome_service/src/db/state.rs` → `:324`; direct tests pinning the contract (not runnable upstream at this pin): `owned_storage_fork_unwinds_while_setter_is_pending` :686, `owned_storage_setter_panics_when_this_thread_holds_read_guard` :743, `owned_storage_setter_from_other_thread_waits_for_read_guard` :850.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "OwnedDb pending_setters with_setter fork", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: optimistic fork with cancellation-on-conflict, RAII pending-writer counter, loud same-thread misuse. Adapt the exception type to your framework's cancellation token. Omit salsa-specific setter semantics; the portable contract is "writers announce, readers bail fast, nobody queues".
