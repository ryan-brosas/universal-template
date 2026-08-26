<!-- capsule-v2 -->
# Workspace uploads — how do thread-scoped JSON/JSONL file uploads reach the agent's workspace without breaking path confinement?

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A porter wiring a chat-UI file upload into a per-thread sandboxed workspace must know how filenames are sanitized, how content is validated before persistence, how the manifest stays consistent across host/remote backends, and how the upload context is surfaced to the model — without escaping the thread workspace or the allowed-suffix gate.

## Thread-scoped upload pipeline
**Path/Symbol:** `src/cuga/backend/server/workspace_upload.py` (whole module, 305 lines); entry `upload_workspace_bytes(thread_id, filename, data)` (178-220); `format_upload_context(thread_id)` (223-239); `resolve_host_workspace_path(user_path, thread_id)` (264-274).
**Signature:** `async def upload_workspace_bytes(thread_id: Optional[str], filename: str, data: bytes) -> dict[str, Any]`; `def format_upload_context(thread_id: Optional[str]) -> str | None`.
**Data Shape:** Allowed suffixes `{".json", ".jsonl", ".ndjson"}`; `MAX_UPLOAD_BYTES = 100 * 1024 * 1024` (matches knowledge `max_upload_size_mb` default). Manifest is `{"thread_id": str, "files": [{name, path, size_bytes, uploaded_at}]}` written as `.manifest.json` under the thread's `uploads/` dir. Returns `{path, sandbox_path, size_bytes, manifest}` where `path` is the display form `workspace/uploads/<name>` and `sandbox_path` is `/workspace/uploads/<name>`.

### Decisive source
```python
def sanitize_upload_filename(filename: str) -> str:
    name = Path((filename or "").strip()).name          # strip any directory
    if not name or name.startswith("."):                 # reject hidden files
        raise ValueError("Invalid filename")
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:                   # extension gate
        raise ValueError(f"Unsupported file type {suffix!r}; ...")
    stem = Path(name).stem
    safe_stem = re.sub(r"[^\w.-]", "_", stem, flags=re.ASCII)  # non-word → _
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("_")       # collapse/trim _
    if not safe_stem:
        raise ValueError("Invalid filename")
    return f"{safe_stem}{suffix}"

def _merge_manifest_entry(manifest, *, thread_id, filename, size_bytes):
    entry = {"name": filename, "path": relative_upload_path(filename),
             "size_bytes": size_bytes,
             "uploaded_at": datetime.now(timezone.utc).isoformat()}
    files = [f for f in manifest.get("files", []) if f.get("name") != filename]
    files.append(entry)                                   # replace same name, keep order
    return {"thread_id": thread_id or "", "files": files}
```

**Flow:** (1) size gate → (2) thread_id required + `safe_thread_id` sanitize → (3) `ensure_thread_workspace_seeded` → (4) `sanitize_upload_filename` → (5) `_unique_upload_name` appends `_<token_hex4>` on collision → (6) `validate_upload_content` (UTF-8, then JSON or per-line JSONL) → (7) write via `write_bytes_under(workspace_base, data, tid, UPLOADS_SUBDIR, name)`; sandbox-backed mode stages a temp `.upload-<hex8>.tmp` and `backend.upload`s it then removes the temp, and writes the manifest BOTH host-side and remote-side. `format_upload_context` returns `None` when no files, else a `## Session uploads` markdown block listing each file's agent path (legacy `/workspace/...` entries normalized via `shell_workspace_path`) and size in MB, with a usage hint that both relative `./uploads/...` and absolute `/workspace/...` are accepted.
**Invariant:** Every path crossing into the workspace goes through `child_path_under` / `write_bytes_under` / `resolve_workspace_path` so an upload can never escape the thread workspace; the manifest is the single source of truth for what the model may reference, and `_agent_path_from_manifest_entry` collapses legacy `shell_path`/`path`/`name` variants to ONE workspace-relative path so stale manifests don't leak host paths into the prompt.
**Probe:** `tests/unit/test_workspace_upload.py` (155 lines) — `test_sanitize_upload_filename_normalizes_browser_download_name` pins `"servicenow_incidents_2entries (1).json" → "servicenow_incidents_2entries_1.json"`; `test_sanitize_upload_filename_strips_path` pins `/tmp/evil/../ok.json → ok.json`; `test_upload_workspace_bytes_host_mode` pins on-disk layout `cuga_workspace/thread-1/uploads/instana.json` + manifest `path == "./uploads/instana.json"` with no `shell_path`; `test_upload_rejects_oversized_file` pins the 100MB gate; `test_format_upload_context_normalizes_legacy_virtual_paths` pins `/workspace/uploads/a.json → ./uploads/a.json`; `test_resolve_host_workspace_path_thread_scoped` pins `workspace/uploads/foo.json → <root>/cuga_workspace/thread-A/uploads/foo.json`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "upload_workspace_bytes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sanitize→validate→persist→manifest pipeline with the exact allowed-suffix set, the `_unique_upload_name` collision suffix, the replace-same-name manifest merge, the dual host/remote manifest write under sandbox backing, and the `format_upload_context` prompt surface (returns `None` when empty, normalizes legacy virtual paths); adapt `MAX_UPLOAD_BYTES`, the display root (`workspace`), and the thread-id format to your host; omit the remote `RemoteSandboxBackend`/`CodeExecutor._get_opensandbox_executor` wiring unless you run an OpenSandbox backend. Direct tests cover the host-mode path fully; the sandbox-backed branch (temp-file staging, remote manifest write, `delete_thread_uploads` sandbox `rm -rf`) has no direct unit test — it is exercised only via the executor integration path.
