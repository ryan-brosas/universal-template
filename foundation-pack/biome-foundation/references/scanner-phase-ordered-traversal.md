<!-- capsule-v2 -->
# Scanner phase-ordered traversal — in what order must a project scan index files so ignore/config state is honored?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** When scanning a project folder, which files must be indexed before the rest and why does the watcher registration precede all handling?

## Scan entry + partitioned traversal
**Path/Symbol:** `crates/biome_service/src/scanner.rs:` `Scanner.index_project` (:145-185), `Scanner.scan` (:321-411), `Scanner.scan_folder` (:417-500).
**Signature:** `fn index_project<W: WorkspaceScannerBridge>(&self, workspace: &W, project_key: ProjectKey, scan_options: ScanOptions) -> Result<ScanProjectResult, WorkspaceError>`; internal `fn scan_folder(&self, folder: &Utf8Path, ctx: &ScanContext<W>) -> ScanFolderResult`.
**Data Shape:** `ScanOptions { scan_kind: ScanKind, force: bool, verbose: bool, watch: bool }`; per-project memo `ScannedProject { scan_kind, watched }` in a papaya HashMap; result `{ diagnostics, duration, configuration_files }`.

### Decisive source
```rust
// index_project: skip only when watched AND not forced; record AFTER the scan.
if !scan_options.force && self.is_watched(&project_path) {
    return Ok(ScanProjectResult { /* all empty */ });
}
let result = self.scan(workspace, project_key, &project_path, IndexTrigger::InitialScan, scan_options)?;
self.projects.pin().insert(project_key, scanned_project);
workspace.notify(ServiceNotification::IndexUpdated);

// scan_folder: evaluate -> sort -> partition -> watch BEFORE handle.
evaluated_paths.sort_unstable();
for path in evaluated_paths {
    if path.is_config() { configs.push(path); }
    else if path.is_manifest() { manifests.push(path); }
    else if path.is_ignore() { ignore_paths.push(path); }
    else if ctx.watch && fs.symlink_path_kind(&path).is_ok_and(PathKind::is_dir) {
        folders_to_watch.insert(path.into());
    } else { handleable_paths.push(path); }
}
let _ = self.watcher_tx.try_send(WatcherInstruction::WatchFolders(folders_to_watch));
fs.traversal(Box::new(|scope| { for path in &configs { scope.handle(ctx, path.to_path_buf()); } }));
fs.traversal(Box::new(|scope| { for path in &manifests { scope.handle(ctx, path.to_path_buf()); } }));
// ... update_project_config_files / update_project_ignore_files ...
fs.traversal(Box::new(|scope| { for path in &handleable_paths { scope.handle(ctx, path.to_path_buf()); } }));
```

**Flow:** index_project → (watched&&!force ⇒ empty early-out) → scan(InitialScan) → scan_folder: evaluate whole tree → sort ascending (root-closest first) → partition into configs/manifests/ignores/handleable/watch-dirs → send WatchFolders *before* any handling → handle configs → manifests → register config/ignore files with workspace → handle remaining files → insert ScannedProject → notify IndexUpdated. `index_folder` re-enters `scan` with trigger=Update, `force: true`, the project's stored watch flag, and **no** IndexUpdated notify (per-file updates notify themselves).
**Invariant:** config/ignore/manifest files are handled before ordinary files because ignore semantics and nested configs change how later files resolve; the root `.gitignore`/config wins over nested ones via ascending sort ("we must process first the `.gitignore` at the root of the project"). The watched-set early-out returns an EMPTY success, not an error.
**Probe:** `crates/biome_service/src/scanner.tests.rs` — `scan_project_result_does_not_expose_source_file_candidates` (:14-42, content readable after scan, configuration_files empty for a plain source file) and `scanner_required_files_are_only_ignored_in_ignored_directories` (:210-256, root package.json indexed regardless of includes, dist/package.json really ignored).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Scanner scan_folder index_project evaluated paths", limit: 10 });
```

## Verdict
Adopt the four-phase ordering (evaluate→partition→watch-register→handle configs-first) and the post-scan ScannedProject insertion; adapt the papaya collections and biome_fs traversal scope to host equivalents; omit the WASM no-thread variant unless targeting wasm32. Coverage: both cited paths `no_recorded_issue`, generation matches pin.
