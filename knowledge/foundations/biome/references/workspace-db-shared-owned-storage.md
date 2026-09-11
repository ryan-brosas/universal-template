<!-- capsule-v2 -->
# Shared vs Owned workspace DB storage — which storage mode does a host need, and how do read forks stay honest?

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** When porting a long-lived tool server that caches parsed sources in an incremental engine, when must the database be a single owned instance versus fork-per-operation, and how are concurrent reads accounted for?

## Two storage modes behind one DbState
**Path/Symbol:** `crates/biome_service/src/db/state.rs:193-201` (`DbState`, `DbStorage`), `:363-376` (`lsp`, `fork`), `:203-230` (`LIVE_READS`, `DbReadGuard`).
**Signature:** `enum DbStorage { Shared(SharedWorkspaceDb), Owned(OwnedDb) }`; `DbState::fork(&self) -> DbReadGuard`; `DbReadGuard::new(db: WorkspaceDb, tracks_live_read: bool)`.
**Data Shape:** Default = `Shared` (CLI: every op forks a throwaway db, writes allocate replacements). `DbState::lsp()` = `Owned`: one canonical `Mutex<WorkspaceDb>` plus `pending_setters: AtomicUsize`.

### Decisive source
```rust
// :371-375 — only Owned mode tracks live reads; Shared forks need no accounting
pub(crate) fn fork(&self) -> DbReadGuard {
    match &self.storage {
        DbStorage::Shared(shared_db) => DbReadGuard::new(shared_db.fork(), false),
        DbStorage::Owned(db) => DbReadGuard::new(db.fork(), true),
    }
}
// :217-220 — the guard is deliberately !Send so the thread-local count stays truthful
pub(crate) struct DbReadGuard {
    db: WorkspaceDb,
    _live_read: LiveReadGuard,
    _not_send: PhantomData<std::sync::MutexGuard<'static, ()>>,
}
```

**Flow:** host picks mode at construction (CLI default / LSP via `lsp()`) → each operation calls `fork()` → Owned mode increments thread-local `LIVE_READS` for the guard's lifetime → setter-based writers consult that count (see fork-setter capsule) → drop decrements.
**Invariant:** A read fork held across a same-thread setter write is a deadlock the type system cannot see; `_not_send` keeps guards on their creating thread so the counter is authoritative. The doc comment (:213-216) admits escapes (`into_untracked_db`, `Deref` clone) and restricts them to read-only leaf operations.
**Probe:** `grep -n '_not_send: PhantomData' crates/biome_service/src/db/state.rs` → exactly 2 hits (`:220` field declaration, `:228` its initialization in `new`); `grep -n 'DbStorage::Owned(db) => DbReadGuard::new(db.fork(), true)'` → sole hit `:374`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "DbState fork DbReadGuard", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-mode split (fork-per-op for batch tools; one owned instance + cancellation for interactive servers) and the !Send read-guard trick for any thread-local accounting. Adapt storage types to your incremental engine. Omit salsa specifics if your memoizer has different write semantics. Caveat: unit tests around this contract exist (state.rs tests module) but the crate's test target does not compile upstream at this pin; evidence here is source + compile-check based.
