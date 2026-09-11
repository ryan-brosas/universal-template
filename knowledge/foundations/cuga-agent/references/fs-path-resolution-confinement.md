<!-- capsule-v2 -->
# Workspace path resolution — POSIX-first virtual `/workspace` mapping with traversal rejection and per-thread seeding

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you give agents one stable absolute root (`/workspace`) across host/remote sandbox modes WITHOUT letting `os.path.normpath` (Windows) or `..` traversal break confinement?

## The canonical resolver + confinement helpers
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/filesystem/paths.py` (`resolve_workspace_path` :208-256; `_posix_path` :146-148; `thread_workspace_root` :134-143; `child_path_under` :70-75; `_normpath_under` :57-67; `assert_resolved_path_under` :78-84; `read_bytes_under` :99-108; `ensure_thread_workspace_seeded` :162-193; `safe_thread_id` :52-54; `shell_workspace_path` :276-294).
**Signature:** `resolve_workspace_path(sandbox_path: str, *, thread_id: str | None, operation: str = "access") -> Path`; `public_workspace_path(host_path, *, thread_id) -> str` (`./x` display form); `write_bytes_under(base, data, *segments) -> Path`.
**Data Shape:** layouts — `thread_id` present → `<cwd>/cuga_workspace/<safe_thread_id>/`, absent → shared `<cwd>/cuga_workspace/`. Accepted inputs: relative paths, `/workspace[...]`, legacy `/tmp[...]` and `/private/tmp[...]` aliases. Failure = `ValueError` ("Path traversal ... not allowed" / "<operation> path must stay under /workspace").

### Decisive source
```python
# :230-231 — POSIX-normalize BEFORE any os.path call; this is the Windows fix
posix = _posix_path(raw)                      # PurePosixPath(raw.replace("\\","/"))
workspace_root = thread_workspace_root(safe_tid).resolve()
...
resolved = dest.resolve()
try:
    resolved.relative_to(workspace_root)      # final containment check
except ValueError as e:
    raise ValueError(f"{operation} path must stay under /workspace") from e

# :57-66 — segment join validates each name and re-checks prefix AFTER normpath
if not clean or clean in (".", "..") or "/" in clean:
    raise ValueError(f"Invalid path segment: {name!r}")
...
if not (fullpath == base_path or fullpath.startswith(base_path + os.sep)):
    raise ValueError(f"Path must stay under {base_path}")
```

**Flow:** strip input → explicit `..` refusal (`_reject_traversal`, loud early failure kept from the old MCP wrapper) → resolve thread root (sanitized id `[A-Za-z0-9_.-]→_`, default `_default`) → map virtual root / legacy roots / relative tail via PurePosix parts joined segment-by-segment through `child_path_under` → `.resolve()` then `relative_to(root)` as the last gate. Per-thread workspaces are seeded ONCE per (base, thread) from opt-in env `CUGA_THREAD_WORKSPACE_SEED=crm,ci`: whitelisted fixture files/dirs copied into EMPTY thread dirs only, in-process `_seeded_threads` memo.
**Invariant:** Never call `os.path.normpath` on the AGENT-facing path — Windows normpath turns `/workspace/x` into `D:\workspace\x` (pinned by a test that monkeypatches a broken normpath). Confinement is enforced twice: structurally during the join AND by resolved-prefix check after symlinks resolve. `read_bytes_under`/`remove_file_under` re-verify realpath under base before touching disk (CWE-22/73 posture for upload/download plumbing).
**Probe:** direct tests `tests/unit/test_resolve_workspace_path.py::test_resolve_manifest_virtual_path_under_thread_workspace` (:23), `::test_resolve_virtual_path_survives_windows_normpath` (:36), `::test_child_path_under_rejects_traversal` (:73), `::test_assert_resolved_path_under_rejects_escape` (:80), `::test_write_and_read_bytes_under_thread_uploads` (:89), `::test_ensure_thread_workspace_seeded_copies_crm_fixtures` (:100); `filesystem/tests/test_workspace_fs.py::test_traversal_is_rejected` (:130 parametrized incl. backslash form), `::test_two_threads_are_isolated` (:106), `::test_shared_assets_seed_into_empty_thread_workspace` (:54).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_workspace_path child_path_under assert_resolved_path_under ensure_thread_workspace_seeded VIRTUAL_WORKSPACE_ROOT", limit: 10 });
```

## Verdict
Adopt POSIX-first normalization + double confinement (segment-validated join, then realpath/prefix check), the two-layout thread_id switch, and one-shot whitelisted seeding of empty thread workspaces. PORTING CAVEAT (pass-20 execution audit): upstream is internally inconsistent at pin — `_SHARED_SEED_FILES` (`paths.py:28-36`) INCLUDES `cuga_knowledge.md` while `test_workspace_fs.py::test_shared_assets_seed_into_empty_thread_workspace` (:72) asserts it must NOT be seeded (suite runs 2-failed/24-passed standalone at HEAD; both files last touched by the same commit `5c93777`) — decide the exclusion list deliberately when porting; do not assume test parity. Adapt root names (`cuga_workspace`, `/workspace`), seed file lists, and legacy aliases to your deployment. Omit the CRM fixture specifics unless you have equivalent demo fixtures.
