<!-- capsule-v2 -->
# Workspace tree backed-detection ladder — when do /workspace APIs hit the host filesystem vs an OpenSandbox SDK?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** Given sandbox_mode × opensandbox_sandbox × enable_shell_tool settings, which storage decides workspace tree/file APIs — and how do legacy UI paths keep resolving?

## workspace_sandbox: detection ladder + legacy aliasing + double confinement
**Path/Symbol:** `src/cuga/backend/server/workspace_sandbox.py:workspace_tree_is_native_backed` (55–67), `.workspace_tree_is_sandbox_backed` (42–52), `public_path_to_sandbox_abs` (222–256), `_native_workspace_resolved` (259–290), fetch/read/preview trio (196–314).
**Signature:** `def workspace_tree_is_native_backed() -> bool`; `def public_path_to_sandbox_abs(path: str) -> str`; `def read_native_workspace_bytes(thread_id, path) -> tuple[bytes, str]`.
**Data Shape:** virtual roots `/workspace` (display "workspace"); legacy display roots `tmp`, `cuga_workspace` and legacy sandbox root `/tmp/cuga_workspace` accepted as aliases.

### Decisive source
```python
def workspace_tree_is_sandbox_backed() -> bool:
    if not bool(getattr(settings.advanced_features, "opensandbox_sandbox", False)): return False
    mode = str(getattr(settings.advanced_features, "sandbox_mode", "opensandbox") or "opensandbox")
    return mode not in ("native", "local")     # flag alone is NOT enough

def workspace_tree_is_native_backed() -> bool:
    plan = ExecutionRouter.resolve(settings)
    if plan.filesystem_backend == "host" or plan.shell_backend in ("native", "local"): return True
    ...
    return bool(getattr(settings.advanced_features, "enable_shell_tool", False))
...
if any(p in ("", ".", "..") or p.startswith(".") for p in tail_parts): raise ValueError("invalid path segment")
resolved.relative_to(root)                     # realpath confinement after alias mapping
```

**Flow:** API handlers branch on the two predicates → native side builds trees via rglob over the per-thread host root hiding dotfiles, maps onto virtual /workspace paths, resolves any accepted alias (workspace | tmp | cuga_workspace | /tmp/... | /tmp/cuga_workspace/...) to segments, rejects "", ".", ".." and dot-prefixed segments BEFORE resolve, then confines with relative_to(root); sandbox side routes the same operations through CodeExecutor/OpenSandbox SDK calls. Previews enforce a 10 MiB cap; missing file/dir mismatches surface as FileNotFoundError/IsADirectoryError.
**Invariant:** opensandbox_sandbox=true does NOT imply sandbox-backed tree APIs while sandbox_mode is native/local; every user path crosses segment validation AND realpath confinement regardless of which alias it arrived through; hidden files never appear in trees.
**Probe:** `tests/unit/test_workspace_sandbox.py` (executed this run: pass — covers native-when-native-mode, native-with-shell-flag, opensandbox-shell-only NOT native, per-thread public roots).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "workspace_tree_is_native_backed public_path_to_sandbox_abs ExecutionRouter resolve", limit: 8 });
```

## Verdict
Adopt the three-input detection ladder (mode beats flag beats shell-tool fallback) and alias-then-confine path resolution. Adapt root names/display strings to your product. Omit the OpenSandbox SDK transport if your sandboxes are E2B/Docker (see sandbox-mode-dispatch capsule for that trio).
