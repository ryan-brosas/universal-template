<!-- capsule-v2 -->
# MCP service-status state machine + background retry loop — why do failed servers become "degraded" instead of "failed", and why must the readiness gate run BEFORE clearing registration?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When an MCP server is slow, down, or flapping at boot, how does the tool registry stay usable — and what state machine keeps the UI honest without blocking startup?

## Per-service status machine + pending-set retry loop
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py` — status builder `_build_status` :81-104 + `_set_service_status` :106-125 + `get_service_statuses` :127-128; declared-state seeding `__init__` :68-75; readiness probe `_check_service_readiness` :710-735; single-server init `_initialize_single_fastmcp_server` :737-883; retry loop `_retry_pending_mcp_servers` :885-903 + `_ensure_retry_task` :905-911; shutdown `shutdown` :130-135.
**Signature:** `_build_status(*, state, message, service_type=None, transport=None, error=None, details=None) -> dict`; states used: `declared` | `starting` | `ready` | `degraded` | `failed`. Retry task: `asyncio.create_task(self._retry_pending_mcp_servers())`, backoff `delay = min(30.0, delay * 1.5 + random.uniform(0.0, 1.0))` seeded at 2.0.
**Data Shape:** `service_statuses[name] = {state, message, updated_at (UTC ISO), [service_type], [transport], [error], [details]}`; readers get a SHALLOW COPY per entry (`status.copy()`), so consumers can't mutate registry state through the getter.

### Decisive source
```python
# mcp_manager.py:737-747 — readiness gates BEFORE teardown of prior registration,
# and failure parks the config in pending_mcp_services rather than dropping it
async def _initialize_single_fastmcp_server(self, name: str, config: ServiceConfig) -> bool:
    ...
    is_ready, readiness_message = await self._check_service_readiness(name, config)
    if not is_ready:
        self.pending_mcp_services[name] = config          # ← retried later, not lost
        self._set_service_status(name, "starting", readiness_message)
        return False

    self._clear_mcp_server_registration(name)             # ← only AFTER ready-check passes
```
```python
# mcp_manager.py:877-883 — connect failure is "degraded", NOT "failed":
#            _set_service_status(
#                name, "degraded",
#                f"Connection failed, retrying in background: {error_msg}",
#                error=error_msg)
```
The distinction matters downstream: `failed` means "config broken, don't expect it"; `degraded` means "keep polling statuses, it may come back". The retry loop exits when the PENDING SET is empty (not on a timer): each tick snapshots `pending.items()`, waits on `self._retry_shutdown.wait()` with timeout as the sleep primitive (so shutdown cancels instantly), then re-inits every pending server. `_ensure_retry_task` is idempotent — it no-ops when nothing is pending or the task is alive, and swaps in a FRESH `asyncio.Event` per task generation (`self._retry_shutdown = asyncio.Event()`), so an old cancelled event can never wedge a new loop.

**Flow:** config load seeds every MCP_SERVER as `declared` / everything else `starting` → `load_tools()` runs initial connects inline (15s `asyncio.wait_for` on `list_tools`) → success: clear stale registration, populate schemas/tools/reverse-map, pop from pending, set `ready`; failure or unready: park in `pending_mcp_services`, set `degraded`/`starting` → background loop retries with jittered exponential backoff capped at 30s until pending drains or `shutdown()` sets `_retry_shutdown` + cancels + `gather(return_exceptions=True)` (never propagates cancellation errors).
**Invariant:** Readiness must be checked BEFORE `_clear_mcp_server_registration(name)` — tearing down first would drop working tools during a transient outage window (delete-then-fail leaves the app absent from `get_app_names(only_ready=True)`). Every terminal transition writes a timestamped status dict; failure paths must ALWAYS park config for retry before returning False, else a boot-time blip permanently removes the server. Error details capture stderr of the spawned stdio process (`transport._process.stderr.read()`) into `initialization_errors` because subprocess launch failures are invisible otherwise.
**Probe:** direct tests pin the sanitization/registration slice this loop feeds — `src/cuga/backend/tools_env/registry/mcp_manager/tests/test_dashed_tool_names.py` (registration-loop mirror `TestSanitizationCollision.test_first_tool_wins_on_collision` :184, `test_colliding_tool_not_registered_twice` :189). Coverage caveat: the retry/backoff loop itself has NO dedicated test — verify by reading :885-911 and simulating two `_initialize_single_fastmcp_server` calls.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_retry_pending_mcp_servers _set_service_status pending_mcp_services _check_service_readiness", limit: 10 });`

## Verdict
Adopt the five-state status machine with copy-on-read, the degraded-vs-failed split, readiness-before-teardown ordering, pending-set-driven jittered retry, and fresh-shutdown-event-per-task. Adapt state names to your domain. Omit the stderr capture if your servers are all HTTP.
