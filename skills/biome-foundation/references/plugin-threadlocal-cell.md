<!-- capsule-v2 -->
# ThreadLocalCell — why raw pthread/Fls keys instead of thread_local!, and what the no-drop rule buys

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** A porter porting per-thread engine slots must reproduce the platform matrix AND the deliberate leak-on-thread-exit semantics.

## Three-platform Key (thread_local.rs)
**Path/Symbol:** `crates/biome_plugin_loader/src/thread_local.rs:4-43` (Windows FLS), `:45-91` (Unix pthread), `:93-126` (wasm32 Cell fallback), `:134-181` (`ThreadLocalCell<T>` wrapper).
**Signature:** `Key<T>` wraps `u32` (FLS) / `libc::pthread_key_t` / `Cell<*mut T>`; `ThreadLocalCell { key: platform::Key<RefCell<T>> }`; entry point `get_mut_or_try_init<F,E>(default: F) -> Result<RefMut<'_,T>,E>`.

### Decisive source
```rust
// thread_local.rs:128-133 — FLS on Windows is load-bearing, not an optimization
/// Thread-local storage.
/// It uses [`Fiber Local Storage`] on Windows,
/// [`pthread_setspecific(3)`] on Unix,
/// or a plain [`Cell`] on single-threaded targets such as WASM.
/// Note that the inner value is not dropped on thread exit to avoid double-free after another
/// [`std::thread_local`] is dropped.
```
```rust
// :175-180 — set() leaks the Box by design; there is no Drop for the inner value
fn set(&self, value: T) {
    let cell = Box::into_raw(Box::new(RefCell::new(value)));
    unsafe { self.key.set(cell); }
}
```

**Flow:** `get_mut_or_try_init` → `get_mut()` reads the raw pointer; NULL means "not initialized in THIS thread" → run default() → `set()` boxes + `into_raw` and stores the pointer → subsequent calls borrow_mut through the pointer. Windows uses **Fiber** Local Storage (`FlsAlloc`) because Boa contexts must stay with their fiber under fiber-based concurrency; plain TLS would hand a different fiber the wrong engine.
**Invariant:** The inner value is INTENTIONALLY never dropped on thread exit (documented double-free hazard when another `std::thread_local` drops). A porter "fixing" the leak with a Drop impl reintroduces the crash class this crate exists to avoid. Also note `get_mut_or_try_init` re-reads via `get_mut().unwrap()` after set (:157) rather than caching — keeps borrow state consistent if default() itself nested a get.
**Probe:** `grep -c 'unsafe impl' crates/biome_plugin_loader/src/thread_local.rs` → `2` (wasm Send/Sync); `grep -n 'FlsAlloc' crates/biome_plugin_loader/src/thread_local.rs` → `16:`; `grep -n 'pthread_key_create' crates/biome_plugin_loader/src/thread_local.rs` → `60:`; `grep -c 'Box::into_raw' crates/biome_plugin_loader/src/thread_local.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"ThreadLocalCell FlsAlloc pthread get_mut_or_try_init","limit":5,"detail":"ids"}'
```
→ resolves the wasm/unix/windows Key impls line-exact.

---
**Verdict:** ADOPT verbatim shape (platform modules + RefCell pointer slot); the no-drop rule and FLS choice are invariants, not implementation details.
