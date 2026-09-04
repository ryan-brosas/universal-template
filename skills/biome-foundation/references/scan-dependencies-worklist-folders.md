<!-- capsule-v2 -->
# Dependency-closure worklist — how do you index only the transitive dependencies a project actually uses, and which folders must then be watched?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How does the scanner expand an initial file set into its used-dependency closure while collecting exactly the folder set that needs watching?

## rayon-scope recursion over is_ignored-gated dependencies
**Path/Symbol:** `crates/biome_service/src/scanner.rs:` `scan_dependencies` (:534-629), fed by `Scanner.index_dependencies` (:231-283) and by `scan`'s second stage (:366-377).
**Signature:** `fn scan_dependencies<W: WorkspaceScannerBridge>(project_path: &Utf8Path, dependencies: ModuleDependencies, ctx: &mut ScanContext<W>) -> (Duration, FxHashSet<Utf8PathBuf>)`.
**Data Shape:** in: dependency paths returned by `index_file`; shared `ctx.dependencies: Mutex<Vec<Utf8PathBuf>>` accumulates transitive hits; out: elapsed duration + `folders_to_watch`.

### Decisive source
```rust
let dependencies: Vec<_> = dependencies.into_iter()
    .filter(|dependency_path| dependency_path.starts_with(project_path))
    .collect();
// Ancestor-folder collection; monotonic early break:
for ancestor in dependency_path.ancestors().skip(1) {
    if ancestor == project_path { break; }
    if !folders.insert(ancestor) {
        // If an ancestor was already in the set, its parents must be too.
        break;
    }
}
rayon::scope(|s| {
    fn index_dependency<'a, W: WorkspaceScannerBridge>(s: &Scope<'a>, ctx: &'a ScanContext<'a, W>, dependency_path: Utf8PathBuf) {
        let dependencies = open_file(ctx, BiomePath::new(dependency_path), ctx.trigger);
        ctx.dependencies.lock().unwrap().extend(dependencies.clone());
        for dependency_path in dependencies {
            let is_ignored = ctx.workspace.is_ignored(
                ctx.project_key, &ctx.scan_kind, &dependency_path,
                IndexRequestKind::Dependency(ctx.trigger), None,
            ).unwrap_or(true);                       // fail CLOSED on error
            if !is_ignored { s.spawn(move |s| index_dependency(s, ctx, dependency_path)); }
        }
    }
    for dependency_path in dependencies { /* same gate, then s.spawn(...) */ }
});
// Second ancestor pass over ctx.dependencies (transitive deps add folders too).
```

**Flow:** filter to paths under project_path → seed ancestor-folder set → parallel worklist: each opened file's imports are re-gated with `IndexRequestKind::Dependency(trigger)` and recursively spawned inside one rayon scope → transitive discoveries accumulate in the mutex → after the scope, drain the mutex and run the SAME early-break ancestor pass → return folders_to_watch (consumers send them via `WatcherInstruction::WatchFolders`).
**Invariant:** ignore errors are fail-closed (`unwrap_or(true)` — an errored check treats the path as ignored). The ancestor early break is sound because ancestor sets are prefix-closed: if a folder is already present, all its ancestors were inserted earlier. Dependency gating uses `IndexRequestKind::Dependency`, distinct from traversal's `Explicit`, so force-ignored files (`!!glob`) can stay unindexed as deps while ordinary ignores are lifted for used dependencies.
**Probe:** `crates/biome_service/src/scanner/workspace_scanner_bridge.tests.rs` — `should_index_an_ignored_file_if_it_is_a_dependency_of_a_non_ignored_file` (:295-334), `should_not_index_a_force_ignored_file_even_if_it_is_a_dependency` (:337-385), `should_index_used_type_definition_of_used_dependency` (:515-547, only `used.d.ts` indexed, sibling `unused.d.ts` not).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "scan_dependencies index_dependency ancestors folders", limit: 10 });
```

## Verdict
Adopt the two-pass closure (worklist + post-scope ancestor fold), the Dependency-vs-Explicit request-kind split, and the fail-closed ignore gate; adapt papaya/rayon plumbing to host concurrency primitives; omit node_modules-specific resolver behavior (that lives in biome_resolver). Coverage: path + tests `no_recorded_issue` at pin.
