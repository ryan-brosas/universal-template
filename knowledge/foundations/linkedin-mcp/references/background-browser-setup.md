<!-- capsule-v2 -->
# Background browser setup — start the server instantly, gate every tool call on readiness

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How does a server whose heaviest dependency is a ~170 MiB browser download start immediately, never serve a tool before the browser exists, and keep its in-memory "ready" state honest against disk?

## Two-stage readiness: lifespan kicks off, per-tool gate enforces
**Path/Symbol:** `linkedin_mcp_server/bootstrap.py` — `configure_browser_environment` (:309-321), `initialize_bootstrap` (:559-566), `start_background_browser_setup_if_needed` (:573-596), `_metadata_shape_ok` (:597-628), `browser_ready` (:630-654), `invalidate_browser_setup` (:668-674), `_run_browser_setup` (:1394-1440), `ensure_tool_ready_or_raise` (:1531-1594); consumer `linkedin_mcp_server/server.py:browser_lifespan` (:88-97); gate entry `linkedin_mcp_server/dependencies.py:get_ready_extractor` (:162-169).
**Signature:** `configure_browser_environment() -> Path`; `start_background_browser_setup_if_needed() -> None`; `browser_ready() -> bool`; `ensure_tool_ready_or_raise(tool_name: str, ctx: Context | None) -> None`.
**Data Shape:** One module-level `BootstrapState` (setup_state ∈ IDLE/RUNNING/READY/FAILED, task handle, timestamps, last_error) plus an install-metadata JSON file under the auth root; disk is truth, the in-memory READY is a cache.

### Decisive source
```python
# :309-321 — normalize AND write back, so metadata, readiness, and the
# patchright subprocess all agree on one string
raw = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or str(browsers_path())
normalized = Path(raw).expanduser().absolute()
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(normalized)
return normalized

# :630-654 — only the full browser counts; headless selects a MODE, not a binary
# (every launch names channel="chromium", so the shell is never started and its
# absence is not a reason to reinstall anything)
revision = targets.get(_FULL_DIR_PREFIX)
if revision is None:
    return False
return _has_install_for(configured, _FULL_DIR_PREFIX, revision)

# :1531-1594 — the per-tool gate: quiescence first, then docker policy, then
# custom-chrome short-circuit, then setup readiness, then auth readiness
if _browser_setup_ready():
    _state.setup_state = SetupState.READY
else:
    if _state.setup_state == SetupState.READY:
        invalidate_browser_setup()          # disk disagrees with the cache
    ...
    raise BrowserSetupInProgressError(
        "...the server is downloading the Patchright Chromium browser in the "
        "background... Do not install the browser yourself... Just wait and "
        "call this tool again in a minute or two.")
```
**Flow:** server lifespan → initialize_bootstrap + start_background_browser_setup_if_needed (managed runtimes only; custom chrome short-circuits straight to READY) → server serves immediately. Each tool call → ensure_tool_ready_or_raise: auth-quiescence check BEFORE any browser-reaching branch → DOCKER policy (host login required) → custom chrome → setup ready? if cached-READY but disk says no: invalidate (drop metadata, reset state) and spawn/reuse the background task → raise BrowserSetupInProgressError with an actionable wait message → else auth ready? else start login. CLI modes (--login/--status/--import-from-browser) use the SYNCHRONOUS `ensure_browser_installed` instead of background setup.
**Invariant:** The gate checks ONLY the full browser, never the shell: a mode-aware gate plus a launch that demands the full browser is an unbounded install loop (gate opens on a shell-only install, launch fails, metadata invalidated, the shell reinstalled). The in-memory READY is a cache that disk can invalidate at any tool call. `configure_browser_environment` must write the normalized path BACK into the environment — a pre-set `~`-prefixed or relative value would otherwise make metadata writes, readiness checks, and the installer subprocess disagree on which directory they mean. A custom executable skips the managed download entirely (downloading a binary that will never run is the whole download spent on nothing).
**Probe:** `tests/test_bootstrap.py` — `TestBootstrap.test_managed_startup_starts_background_setup` (:88-106) pins lifespan→RUNNING+task; `test_setup_in_progress_raises` (:108-116) pins the gate raise; `TestBrowserReady` (:496-548) pins full-only-ready / shell-only-not-ready / stale-schema-rejected; `TestSetupGate` (:958-1014) pins both modes × both installs through the real gate; `TestEnsureToolReadyInvalidatesStaleReady` (:3396-3431) pins cache-vs-disk invalidation (metadata gone, state RUNNING, task spawned); `TestConfigureBrowserEnvironment` (:3432-3472) pins env write-back for pre-set/tilde/relative values.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "start_background_browser_setup_if_needed browser_ready ensure_tool_ready_or_raise configure_browser_environment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split for any server with a heavy one-time dependency: kick off provisioning in the lifespan, enforce it per-request with a typed "still working, do not help" error, and treat in-memory readiness as a cache that the disk may invalidate. Adopt the single-binary readiness predicate when your launcher names one binary regardless of mode. Adapt the metadata schema and the env-var write-back to your runner's own path contract. Omit the patchright-specific registry reads. Coverage caveat: none — bootstrap.py fully indexed at the pin (no_recorded_issue); graph unavailable this pass, citations verified by direct read.
