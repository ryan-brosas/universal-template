<!-- capsule-v2 -->
# Watcher event dispatch matrix — how do noisy cross-platform notify events map onto index/unload/rename operations without phantom updates?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How must a file watcher translate EventKind/ModifyKind variants (which differ per OS) into exactly one index or unload action per real filesystem change?

## EventKind match + existence-probe fallbacks
**Path/Symbol:** `crates/biome_service/src/scanner/watcher.rs:` `Watcher.handle_notify_event` (:253-312), `watched_paths` (:315-333), `rename_path` (:421-437), `Watcher::new` bounded channel (:150-161), `WatcherInstructionChannel::drop` (:110-118).
**Signature:** `fn handle_notify_event(workspace: &impl WorkspaceWatcherBridge, event: NotifyEvent) -> Vec<Diagnostic>`; run loop `pub fn run(&mut self, workspace: &impl WorkspaceWatcherBridge)` selects over notify_rx vs instruction_rx.
**Data Shape:** `notify` events on a deliberately `bounded::<NotifyResult<NotifyEvent>>(128)` channel; instructions `WatchFolders(FxHashSet<Utf8PathBuf>) | UnwatchFolder | ReindexFile | Stop` on an unbounded channel.

### Decisive source
```rust
EventKind::Modify(modify_kind) => match modify_kind {
    ModifyKind::Name(RenameMode::From) => Self::unload_paths(workspace, paths),
    ModifyKind::Name(RenameMode::To) => Self::index_paths(workspace, paths),
    ModifyKind::Name(RenameMode::Both) => match paths.len() {
        2 => Self::rename_path(workspace, &paths[0], &paths[1]),
        1 => if paths[0].exists() { Self::index_paths(workspace, paths) }
             else { Self::unload_paths(workspace, paths) },   // which end survived?
        _ => Ok(vec![]),
    },
    // RenameMode::Any + ModifyKind::Any are REQUIRED catch-alls: without them
    // events are missed on Windows/macOS. macOS can emit Modify(Data) after removal.
    ModifyKind::Data(_) | ModifyKind::Name(RenameMode::Any) | ModifyKind::Any => {
        if paths[0].exists() { Self::index_paths(workspace, paths) }
        else { Self::unload_paths(workspace, paths) }
    }
    _ => Ok(vec![]),
}
```
```rust
// Every event path is filtered to watched, non-ignored project paths first:
workspace.find_project_with_scan_kind_for_path(&path)
    .and_then(|(project_key, scan_kind)| match
        workspace.is_ignored(project_key, &scan_kind, &path, None) {
            Ok(is_ignored) => (!is_ignored).then_some(path),
            Err(_) => None,                       // error ⇒ drop the event
        })
```

**Flow:** run-loop `select!`: Ok(Ok(event)) → filter via watched_paths (empty ⇒ return) → EventKind matrix → errors only warn. Watch registration (`watch_folders`) dedups against the scanner's watched set BEFORE adding to notify and batch-commits; unwatch removes every watched path that starts_with the removed folder. Stop arrives via instruction OR sender drop (`impl Drop for WatcherInstructionChannel` sends `Stop`), and the loop always ends with `workspace.notify_stopped()` — including on watcher-error break.
**Invariant:** at most one index/unload per real change; ambiguous single-path rename events are disambiguated by an existence probe, never guessed. Access/Any/Other events are no-ops. The notify channel is bounded on purpose ("watchers are intrinsically unreliable... no justification for unbounded memory").
**Probe:** `crates/biome_service/src/scanner/watcher.tests.rs` — `should_index_on_write_but_not_on_read` (:27-97, fs::read triggers nothing; fs::write indexes exactly 1 file) and `should_index_on_create_and_unload_on_delete` (:101-163, create→index, delete→indexed_files back to empty).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "handle_notify_event RenameMode watched_paths unload_paths", limit: 10 });
```

## Verdict
Adopt the total EventKind matrix with existence-probe disambiguation and the pre-filter of every event path through project+ignore resolution; adapt the notify backend and RenameMode coverage to host platforms; omit PollWatcher/BIOME_WATCHER_* env CLI unless a daemon port needs it. Coverage: path + tests `no_recorded_issue` at pin.
