<!-- capsule-v2 -->
# Sandbox workspace snapshot persistence — how do native snapshot references round-trip through a tar-typed API, and what wins when unmount/remount fails mid-snapshot?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** The persistence API is typed as `persist_workspace() -> io.IOBase` (tar bytes) and `hydrate_workspace(data: io.IOBase)`. How do you smuggle a native provider snapshot (an opaque id, not bytes) through that contract, when must you fall back to real tar, and how do you order errors when mounts must be unmounted before the snapshot and remounted after?

## Magic-prefixed snapshot envelopes + phase-ordered error precedence
**Path/Symbol:** `src/agents/extensions/sandbox/e2b/sandbox.py:` `persist_workspace` (:1380–1383), `_persist_workspace_via_snapshot` (:1385–1482), `_persist_workspace_via_tar` (:1484–1557), `hydrate_workspace` (:1559–1672), `_encode_e2b_snapshot_ref`/`_decode_e2b_snapshot_ref` (:173–192), `_E2B_SANDBOX_SNAPSHOT_MAGIC` (:57), `_run_persist_workspace_command` (:1343–1378, `@retry_async` retry_if provider-timeout/transient-status); `src/agents/extensions/sandbox/modal/sandbox.py:` `_persist_workspace_via_snapshot_filesystem` (:1296–1411), `_encode_modal_snapshot_ref`/`_decode_modal_snapshot_ref` (:338–393), `_hydrate_workspace_via_tar` (:1953+), `_write_process_stdin` (:273–283, bounded-chunk stdin).
**Signature:** `async def persist_workspace(self) -> io.IOBase`; `async def hydrate_workspace(self, data: io.IOBase) -> None`; `def _decode_e2b_snapshot_ref(raw: bytes) -> str | None`; `def _decode_modal_snapshot_ref(raw: bytes) -> tuple[WorkspacePersistenceMode, str] | None`.
**Data Shape:** Envelope = magic prefix + compact JSON. e2b: `b"E2B_SANDBOX_SNAPSHOT_V1\n"` + `{"snapshot_id": ...}`. Modal: two magics (`_MODAL_SANDBOX_FS_SNAPSHOT_MAGIC` / `_MODAL_SANDBOX_DIR_SNAPSHOT_MAGIC`) + `{"snapshot_id": ..., "workspace_persistence": ...}` — the mode is both the magic tag and a validated body field with a magic-derived default.

### Decisive source
```python
# e2b: native snapshot only when nothing plain must be excluded
if skip - mount_skip_rel_paths:
    return await self._persist_workspace_via_tar()   # native snapshots can't exclude paths
...
snap = await asyncio.wait_for(_sandbox_create_snapshot(self._sandbox),
                              timeout=self.state.timeouts.snapshot_tar_s)
snapshot_id = getattr(snap, "snapshot_id", None)
...
return io.BytesIO(_encode_e2b_snapshot_ref(snapshot_id=snapshot_id))
```
and the remount-first error precedence:
```python
if remount_error is not None:
    if snapshot_error is not None:
        remount_error.context["snapshot_error_before_remount_corruption"] = ...
    raise remount_error          # half-mounted workspace beats lost snapshot
if unmount_error is not None:
    raise unmount_error
if snapshot_error is not None:
    raise snapshot_error
```
and hydration dispatching on the magic:
```python
snapshot_id = _decode_e2b_snapshot_ref(bytes(raw))
if snapshot_id is not None:
    await _sandbox_kill(self._sandbox)          # best-effort; old sandbox is replaced
    sandbox = await _sandbox_create(SandboxClass, template=snapshot_id, ...)
    self._sandbox = _as_sandbox_api(sandbox)
    self.state.sandbox_id = str(_sandbox_id(sandbox))
    self._workspace_root_ready = True
    return
validate_tar_bytes(bytes(raw), allow_external_symlink_targets=False)  # tar path: fail closed
```

**Flow:** Persist picks native-vs-tar by capability and skip-path shape: no `create_snapshot` method ⇒ tar; plain (non-mount) skip paths present ⇒ tar (native snapshots capture the whole sandbox and cannot exclude); only mount-target skips ⇒ unmount each mount (`teardown_for_snapshot`), snapshot with a timeout, remount in REVERSE order (`restore_after_snapshot`), and encode the id into the magic envelope. Every phase records its error and continues remounting the remaining mounts — additional remount failures accumulate into `context["additional_remount_errors"]` rather than masking the first. Tar persist shells out `tar -C root -cf - . | base64 -w0` (excludes from the session's skip list), validates the base64 (`b64decode(validate=True)`), and runs under `retry_async` gated on provider timeouts/transient HTTP statuses. Modal's filesystem-snapshot variant adds an ephemeral-path dance: back up skip paths to an in-memory tar, `rm -rf` them, snapshot a clean tree, then restore from the backup — with restore attempted on cleanup failure AND on snapshot failure before raising. Hydration decodes the magic first: a native ref replaces the sandbox (kill old, create from `template=snapshot_id`, re-key state, mark root ready); raw tar is validated fail-closed (`UnsafeTarMemberError` ⇒ `WorkspaceArchiveWriteError` with member detail), uploaded, extracted with exit-code checking, and the temp tar is always `rm -f`'d in `finally` (errors swallowed).

**Invariant:** (1) The tar-typed API is preserved at the boundary — native snapshots ride inside it as magic-prefixed envelopes, so callers and storage never need a second channel. (2) Tar fallback is triggered by expressiveness, not by failure: if the snapshot cannot represent the required exclusions, use tar BEFORE trying. (3) Error precedence is corruption-first: remount failures outrank snapshot failures, and the snapshot error is preserved as context (`snapshot_error_before_remount_corruption`) because a workspace left half-mounted is strictly worse than a lost snapshot. (4) Hydration trusts nothing: magic-or-tar dispatch, fail-closed tar validation, exit-code-checked extraction, guaranteed temp cleanup.

**Probe:** `tests/extensions/sandbox/test_e2b.py` — `test_e2b_persist_workspace_native_snapshot_returns_snapshot_ref` (:1625), `test_e2b_persist_workspace_native_snapshot_times_out_and_remounts_mounts` (:1636), `test_e2b_persist_workspace_native_snapshot_falls_back_to_tar_for_plain_skip_paths` (:1669), `test_e2b_persist_workspace_remounts_mounts_after_snapshot` (:1747), `test_e2b_persist_workspace_keeps_remounting_and_raises_remount_error_first` (:1849), `test_e2b_persist_workspace_remounts_prior_mounts_after_unmount_failure` (:1814), `test_e2b_hydrate_workspace_native_snapshot_recreates_from_snapshot_id` (:1687), `test_e2b_hydrate_workspace_raises_on_nonzero_extract_exit` (:1733); `tests/extensions/sandbox/test_modal.py` — `test_modal_resume_restores_snapshot_when_workspace_readiness_unproven` (:1468, `_encode_snapshot_filesystem_ref` round trip), `test_modal_resume_restores_directory_snapshot_when_workspace_readiness_unproven` (:1503), persist assertions at :2373/:2462 (archive bytes == encoded refs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "persist workspace snapshot magic envelope tar fallback teardown_for_snapshot restore_after_snapshot remount error precedence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the magic-prefix envelope pattern for any API pinned to an opaque-bytes type that must also carry provider-native references, and the corruption-first error precedence (remount > unmount > snapshot) for any unmount→capture→remount cycle. Adopt capability+expressiveness-gated fallback (not failure-gated). Adapt the envelope fields to your provider (modal's mode-tagged dual magic shows the multi-variant form). Omit the ephemeral backup/restore dance unless your snapshot excludes paths by deletion. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
