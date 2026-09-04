<!-- capsule-v2 -->
# FS rayon traversal engine — how does a parallel directory walk stay deduplicated across symlinks and threads?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How do you parallelize recursive filesystem traversal without visiting a path twice or spawning handlers for files the consumer cannot process?

## Intern-gated recursion over a rayon scope
**Path/Symbol:** `crates/biome_fs/src/fs.rs:` `TraversalScope`/`TraversalContext` traits (:397-445); `crates/biome_fs/src/fs/os.rs:` `OsTraversalScope` (:174-223), `handle_any_file` (:271-390); `crates/biome_fs/src/interner.rs:` `PathInterner` whole (47L).
**Signature:** `fn evaluate(&self, ctx: &'scope dyn TraversalContext, path: Utf8PathBuf)`; `fn intern_path(&self, path: Utf8PathBuf) -> bool`.
**Data Shape:** `PathInterner { storage: papaya HashSet<Utf8PathBuf, FxBuildHasher>, handler: Sender<Utf8PathBuf> }` built as `(Self, Receiver<Utf8PathBuf>)` from an `unbounded` crossbeam channel; context callbacks `can_handle/handle_path/store_path/push_diagnostic` plus `evaluated_paths()` returning the papaya `HashSetRef`.

### Decisive source
```rust
let origin_path_exist = origin_path.is_some();
if !ctx.interner().intern_path(path.clone()) {
    // If the path was already inserted, it could have been pointed at by
    // multiple symlinks. No need to traverse again.
    return;
}
if file_type.is_symlink() {
    if !ctx.can_handle(&BiomePath::new_with_kind(path.clone(), PathKind::File { is_symlink: true })) { return; }
    let (target_path, target_file_type) = expand_symbolic_link(&path)...;
    if !ctx.interner().intern_path(target_path.clone()) { return; }  // target ALSO interned
    ...
}
```

**Flow:** `FileSystem::traversal(BoxedTraversal)` opens a rayon `scope`; OS impl transmutes it into a `#[repr(transparent)] OsTraversalScope` (SAFETY: layout-identical). `evaluate` absolutizes the input, stats it, and recursion proceeds: intern → symlink expansion (interning BOTH link and target) → `can_handle` gate → directories spawn `handle_dir` on the rayon scope, files go to `store_path`, non-file/non-dir types become Warning diagnostics. Inside symlinked dirs the `origin_path` is REBUILT per entry (`origin_path.join(file_name)`) so ignore patterns match against the unresolved path.
**Invariant:** `intern_path` returns `true` only for first-seen paths and emits them on the channel exactly once — every spawned traversal task is unique by construction; no `can_handle` check is skipped before spawning work. The interner's contains-check-then-insert under a single pinned guard is the dedup point of the whole engine. Memory twin (`fs/memory.rs`) replaces recursion with prefix-filtered key iteration + injected `ErrorEntry` diagnostics, proving the TraversalContext contract is the portability seam.
**Probe:** `cargo test -p biome_fs --lib` executed at pin: **12/12 GREEN**, including `path::test::test_biome_paths_order`/`test_biome_file_names_order` (priority ordering) and `fs::memory::tests::traversal` (:519-585 — pins evaluate-by-prefix + store_path/can_handle choreography via a TestContext).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TraversalScope evaluate PathInterner intern_path handle_any_file can_handle", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: `PathInterner.intern_path` :31-42, `TraversalContext.interner` fs.rs :418, `OsTraversalScope.evaluate` os.rs :196-216, `MemoryTraversalScope.evaluate` memory.rs :307-349 line-exact.

## Verdict
Adopt intern-before-traverse dedup with the two-interns-per-symlink rule and the can_handle-before-spawn gate; adapt the thread-pool substrate (rayon scope here) and the absolutize step to your host; omit the origin-path reconstruction only if your ignore matcher resolves symlinks itself. Coverage: all three files `no_recorded_issue`/`generation_matches` at pin; sources read whole (os.rs 506L, interner.rs 47L, memory.rs 586L).
