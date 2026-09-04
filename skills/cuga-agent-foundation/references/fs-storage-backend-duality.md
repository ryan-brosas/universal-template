<!-- capsule-v2 -->
# Storage backend duality — one LLM tool surface over host-tree vs remote-sandbox storage primitives

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you keep identical LLM-facing filesystem semantics when storage is a local directory in one mode and a remote sandbox HTTP API in another — including the behaviors that DON'T transfer?

## FilesystemBackend ABC + two implementations
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_graph/nodes/cuga_lite/executors/filesystem/backends.py` (ABC `FilesystemBackend` :36-70; `HostWorkspaceBackend` :78-191; `RemoteSandboxBackend` :199-311).
**Signature:** ABC primitives: `read_text(path, *, operation)`, `write_text(path, content, *, operation) -> display_path`, `exists`, `mkdir -> display`, `move(src, dst) -> (src_display, dst_display)` raising on existing destination, `list_dir(path, pattern) -> ListFilesResult`, `search(path, pattern, exclude) -> [paths]`, `stat -> dict`, `download(sandbox_path, filename?) -> DownloadResult`, `upload(local_path, sandbox_path) -> UploadResult`.
**Data Shape:** `WorkspaceFilesystem` (behavior: slicing, diffs, JSON contracts) composes one backend (storage). `HostWorkspaceBackend(thread_id)` roots at the per-thread/shared workspace; `RemoteSandboxBackend(executor, thread_id)` adapts OpenSandboxExecutor's `interpreter.sandbox.files.*`.

### Decisive source
```python
# Host move (:110-113): local atomic rename with explicit pre-check
if dst.exists():
    raise ValueError(f"Destination already exists: {destination}")
dst.parent.mkdir(parents=True, exist_ok=True)
os.rename(src, dst)

# Remote list_dir is_dir heuristic (:265): no stat() across the wire
is_dir=(e.size == 0 and str(oct(e.mode)).startswith("0o7"))

# Host download self-alias guard (:175); remote upload confinement (:305)
if dest.resolve() != src.resolve(): dest.write_bytes(data)
...
payload = read_bytes_under(Path(local_path), base)   # realpath-under-base or raise
```

**Flow:** host mode resolves every path through the canonical resolver and returns `./` public display paths; remote mode instead normalizes through `_normalize_sandbox_path` (`/tmp`→`/workspace`), lazily gets the per-thread interpreter (`_get_or_create_interpreter(self.thread_id)` — remote sandboxes are ALREADY thread-isolated, so no subdir logic), and shells out `mkdir -p` before writes/moves. `exists()` remotely = get_file_info probe wrapped so ANY exception means False.
**Invariant:** The ABC contract is behavioral, not just structural — "move fails when destination exists" must hold in BOTH modes (remote implements it via an exists() probe before `mv`, accepting a small TOCTOU window the host doesn't have). Display paths differ by design: host renders `./relative`, remote echoes sandbox paths. Transfer plumbing (download/upload) exists in both but stays off the LLM surface; upload is confined to the local base dir via `read_bytes_under`/`assert_resolved_path_under` in both.
**Probe:** direct tests `filesystem/tests/test_workspace_fs.py::test_move_file_fails_when_destination_exists` (:194), `::test_download_upload_callable_but_not_structured_tools` (:229 exercises host download/upload round-trip), `::test_list_files_surfaces_writes_not_siblings` (:156 asserts thread isolation of listings); remote-mode specifics carry NO direct unit tests (requires live opensandbox executor) — coverage caveat: `RemoteSandboxBackend` verified by source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "FilesystemBackend HostWorkspaceBackend RemoteSandboxBackend _get_or_create_interpreter", limit: 10 });
```

## Verdict
Adopt the split: ONE behavior class owning LLM semantics + thin storage backends behind a primitive ABC whose docstrings pin cross-backend contracts (move-exists failure, parent creation, display-path return). Adapt the remote adapter to your sandbox's file API and re-derive its `is_dir` heuristic from what your API actually returns. Omit the opensandbox executor coupling; depend on an injected executor object.
