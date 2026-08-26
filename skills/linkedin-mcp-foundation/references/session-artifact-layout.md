<!-- capsule-v2 -->
# Session artifact layout — what files make up one reusable logged-in profile?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** Which files constitute a session, and how do derived runtimes reuse a source login without sharing its Chromium identity?

## Four artifacts per login, derived per runtime
**Path/Symbol:** `linkedin_mcp_server/session_state.py:SourceState`, `RuntimeState`, `get_runtime_id()` (:44-70, :145).
**Signature:** `SourceState(version, source_runtime_id, login_generation, created_at, profile_path, cookies_path)`; `RuntimeState(version, runtime_id, source_runtime_id, source_login_generation, created_at, committed_at, profile_path, storage_state_path, commit_method)`.
**Data Shape:** One auth root (`auth_root_dir()` = parent of the configured profile dir) holds: `profile/` (the Chromium user-data dir), `cookies.json` (portable export), `source-state.json` (`SourceState`), and `runtime-profiles/<runtime_id>/profile/` + `storage-state.json` + `RuntimeState` per consuming runtime.

### Decisive source
```python
def get_runtime_id() -> str:
    """Return a deterministic identity for the current browser runtime."""
    os_name = _normalize_os(platform.system())
    arch = _normalize_arch(platform.machine())
    runtime_kind = "container" if _is_container_runtime() else "host"
    return f"{os_name}-{arch}-{runtime_kind}"
```
Login writes `login_generation=str(uuid4())` (:459) into `SourceState`; every derived `RuntimeState` records `source_login_generation` so a consumer knows WHICH source generation it came from.

**Flow:** source login → validate → write `SourceState` + export `cookies.json` → each consuming runtime imports cookies into its own `runtime-profiles/<id>/profile/`, commits `storage-state.json` and stamps `RuntimeState.commit_method`.
**Invariant:** `login_generation` is written only after LinkedIn validated the session and cookies were exported — it is the token meaning "a usable session exists here". Runtime ids are deterministic (`{os}-{arch}-{host|container}`, arch aliases x86_64→amd64, arm64/aarch64→arm64) so a session prepared on one runtime kind imports on matching kinds without coordination.
**Probe:** `tests/test_session_state.py` (855L) pins state-file round-trips; `tests/test_browser_import_extract.py` pins cookie import/extract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "SourceState RuntimeState get_runtime_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-artifact layout + deterministic runtime id + generation stamping for any multi-runtime browser-session reuse. Adapt artifact names/paths to host conventions. Omit LinkedIn specifics.
