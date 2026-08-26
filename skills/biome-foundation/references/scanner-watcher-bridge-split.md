<!-- capsule-v2 -->
# Scanner/watcher bridge split — how do two background subsystems get workspace access without either widening the other's surface?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** When a scanner and a watcher both need workspace operations, how do you keep their capabilities explicitly scoped and the watcher's a provable subset of the scanner's?

## Two traits + one deliberate adapter
**Path/Symbol:** `crates/biome_service/src/scanner/workspace_bridges.rs:` `WorkspaceScannerBridge` (:14-113), `WorkspaceWatcherBridge` (:117-196), `ScannerWatcherBridge` (:205-317); server wiring `crates/biome_service/src/workspace/server.rs:` `WorkspaceServerWithDb::start_watcher` (:557-559).
**Signature:** `pub(crate) trait WorkspaceScannerBridge: Send + Sync + RefUnwindSafe { fn fs(&self) -> &dyn FileSystem; fn is_ignored(&self, ..., request_kind: IndexRequestKind, path_kind: Option<PathKind>) -> ...; fn index_file(&self, project_key, path, trigger: IndexTrigger) -> Result<(ModuleDependencies, Vec<Error>), WorkspaceError>; ... }` vs `pub trait WorkspaceWatcherBridge { fn index_file(&self, project_key, path) -> Result<Vec<Diagnostic>, _>; ... }`.
**Data Shape:** adapter holds only borrows: `ScannerWatcherBridge<'a, W> { scanner: &'a Scanner, workspace: &'a W }`.

### Decisive source
```rust
/// This creates a bit of duplication and indirection ... but it forces us to
/// consider how we export workspace functionality a bit more carefully. We want
/// the functionality exposed to the watcher to align with what's exposed to the
/// scanner in general, so this is very much intentional.   // :198-204 comment
impl<W: WorkspaceScannerBridge> WorkspaceWatcherBridge for ScannerWatcherBridge<'_, W> {
    fn find_project_with_scan_kind_for_path(&self, path: &Utf8Path) -> Option<(ProjectKey, ScanKind)> {
        self.workspace.find_project_for_path(path)
            .and_then(|project_key| self.scanner.get_scan_kind_for_project(project_key)
                .map(|scan_kind| (project_key, scan_kind)))
    }
    fn is_ignored(&self, project_key, scan_kind, path, path_kind) -> Result<bool, WorkspaceError> {
        self.workspace.is_ignored(project_key, scan_kind, path,
            IndexRequestKind::Explicit(IndexTrigger::Update), path_kind)   // pinned trigger
    }
    fn index_folder(&self, path: &Utf8Path) -> Result<Vec<Diagnostic>, WorkspaceError> {
        let Some(project_key) = self.find_project_for_path(path) else { return Ok(vec![]); };
        self.scanner.index_folder(self.workspace, project_key, path)       // routed back
    }
}
// server.rs:557 — blocking run on the caller's thread:
pub fn start_watcher(&self, mut watcher: Watcher) {
    watcher.run(&ScannerWatcherBridge::new((&self.scanner, self)));
}
```

**Flow:** traversal code is generic over `WorkspaceScannerBridge` (Send+Sync+RefUnwindSafe because scanner threads and catch_unwind need it); the watcher thread receives only a `WorkspaceWatcherBridge`, which the adapter implements by (1) delegating reads to the workspace, (2) resolving scan kinds from the *scanner's* project table, (3) pinning all watcher-triggered ignore checks/indexes to `IndexTrigger::Update`, and (4) routing folder indexing back through `Scanner.index_folder` so scan bookkeeping stays in one place.
**Invariant:** the watcher can never call a scanner-invisible operation — its surface is constructed as a projection of the scanner surface, not an independent implementation; out-of-project paths short-circuit to empty success (`Ok(vec![])`), never errors. Mock test double exists for the narrow trait only (`scanner/test_utils.rs MockWorkspaceWatcherBridge`).
**Probe:** `crates/biome_service/src/scanner/workspace_scanner_bridge.tests.rs` — `close_file_through_watcher_before_client` (:29-98) and `close_file_from_client_before_watcher` (:101-159): client open/close vs watcher index/unload interleave through the bridge without losing content or leaving stale index entries.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ScannerWatcherBridge WorkspaceWatcherBridge start_watcher", limit: 10 });
```

## Verdict
Adopt the wide-trait/narrow-trait + borrow-only adapter pattern for any multi-subsystem host service; adapt the trigger pinning to your update taxonomy; omit the RefUnwindSafe bound only if the host forbids catch_unwind isolation. Coverage: both paths `no_recorded_issue`, generation matches pin.
