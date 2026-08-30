<!-- capsule-v2 -->
# Sandbox session lifecycle and resume — how do you reconnect to a live remote sandbox, fall back to recreation, and shut down without leaking or losing state?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** A sandbox session is serialized (sandbox id + options), the process dies, and later resumes. How does the adapter re-attach to the still-running remote sandbox, decide when the remote is dead, recreate from template without losing state, and tear down best-effort on both pause and kill policies?

## Reconnect-first resume + best-effort shutdown
**Path/Symbol:** `src/agents/extensions/sandbox/e2b/sandbox.py:` `E2BSandboxClient.create` (:1690–1772), `E2BSandboxClient.resume` (:1773–1838), `_sandbox_connect` (:503–517), `_sandbox_create` (:445–490, signature-introspected kwargs filtering), `_e2b_lifecycle` (:492–500), `_shutdown_backend` (:861–897), `_import_sandbox_class` (:333–355), `_e2b_network_config` (:1841–1844); `src/agents/extensions/sandbox/modal/sandbox.py:` `ModalSandboxSession._ensure_sandbox` (:677–762), `_call_modal` (:556–570), `_shutdown_backend` (:649–675), `_override_modal_image_builder_version` (:243–260), `_maybe_set_sandbox_cmd` (:263–269), `ModalSandboxClient.resume` (:2285+).
**Signature:** `async def resume(self, state: SandboxSessionState) -> SandboxSession`; `async def _ensure_sandbox(self) -> bool` (returns True when rehydrated from a persisted id, False when freshly created); `async def _call_modal(self, fn, *args, call_timeout=None, **kwargs) -> R`.
**Data Shape:** `E2BSandboxSessionState` / `ModalSandboxSessionState` carry `sandbox_id`, template/image identity, timeouts, `pause_on_exit`/`on_timeout` ("kill"|"pause"), `workspace_persistence` ("tar"|"snapshot"), exposed ports, and provider extras (mcp config for e2b; gpu/cpu/memory/idle_timeout/image_builder_version for modal). Resume mutates state in place: new `sandbox_id` + `workspace_root_ready=False` on recreation.

### Decisive source
```python
# e2b resume: reconnect ladder, paused-sandbox probe skip, dead-sandbox recreation
sandbox = await _sandbox_connect(SandboxClass, sandbox_id=state.sandbox_id,
                                 timeout=state.sandbox_timeout)
if not state.pause_on_exit and not preserves_timeout_paused_state:
    is_running = await _sandbox_is_running(sandbox, request_timeout=state.timeouts.keepalive_s)
    if not is_running:
        raise RuntimeError("sandbox_not_running")
    reconnected = True
except Exception:
    sandbox = await _sandbox_create(SandboxClass, template=state.template, ...)
if not reconnected:
    state.sandbox_id = str(_sandbox_id(sandbox))
    state.workspace_root_ready = False
```
and the modal lazy (re)hydration with poll-based liveness:
```python
if sid:
    try:
        sb = await self._call_modal(modal.Sandbox.from_id, sid, ...)
        poll_result = await self._call_modal(sb.poll, ...)
        if poll_result is None:            # None == still running
            self._sandbox = sb; self._running = True; return True
    except Exception:
        pass
    self._sandbox = None; self.state.sandbox_id = None   # dead handle: clear, recreate
app = await self._call_modal(modal.App.lookup, self.state.app_name, create_if_missing=True, ...)
```

**Flow:** e2b `create` coerces the sandbox type (code-interpreter vs plain e2b), resolves timeouts (model-validate dicts), merges envs (manifest envs override client envs), builds the network config (exposed ports ⇒ `{"allow_public_traffic": True}` — no ports ⇒ None so the key is never sent), and filters create kwargs through `inspect.signature` of the SDK's `create` (unknown keys dropped; `lifecycle` passed only when the SDK accepts it — version tolerance again). `_sandbox_connect` prefers the full wrapper (`connect` → `_cls_connect_sandbox` → `_cls_connect`, swallowing only TypeError between rungs). Resume computes `preserves_timeout_paused_state = state.on_timeout == "pause"`: a paused sandbox reports not-running BY DESIGN, so the liveness probe is skipped for pause-policy states; a dead kill-policy sandbox falls into recreation from the stored template and the state is re-keyed. `_shutdown_backend` is best-effort: pause_on_exit tries pause, falls back to kill on failure, and logs (never raises) both failures. Modal inverts the timing: `_ensure_sandbox` runs lazily before any exec/port/snapshot call; image resolution is image_id → registry tag (default tag recorded back into state for debuggability) → `sleep infinity` cmd overlay so the sandbox idles instead of exiting; `Sandbox.create` runs under a process-local image-builder-version override (modal_config.override_locally + env restore in finally); `_shutdown_backend` rehydrates the handle from id if needed, terminates with a timeout, swallows every error, and ALWAYS clears `sandbox_id`/handle/`workspace_root_ready` in finally.

**Invariant:** (1) Resume never gives up: reconnect → liveness-probe (policy-aware) → recreate-from-template, and the state always ends consistent with the sandbox actually in hand (new id + readiness reset on recreation). (2) A pause-policy sandbox must not be judged dead by its own pause semantics — liveness probes are gated on the timeout policy. (3) Shutdown is advisory: cleanup failures are logged and swallowed, but the local state is unconditionally cleared so a stale handle can never be reused. (4) SDK version drift is absorbed at the boundary — introspected create kwargs, best-effort connect ladder, `.aio`-or-executor call wrapper.

**Probe:** `tests/extensions/sandbox/test_e2b.py` — `test_e2b_resume_reuses_paused_timeout_lifecycle_sandbox` (:1317), `test_e2b_resume_reuses_live_kill_timeout_sandbox` (:1368), `test_e2b_resume_recreates_dead_kill_timeout_sandbox_and_preserves_mcp` (:1420), `test_e2b_client_create_enables_public_traffic_for_exposed_ports` (:1094), `test_e2b_client_create_omits_auto_resume_for_kill_timeout` (:1161), `test_e2b_client_create_passes_mcp_config` (:1213), `test_e2b_sandbox_connect_prefers_full_sandbox_wrapper` (:776); `tests/extensions/sandbox/test_modal.py` — `test_modal_resume_eagerly_reconnects_sandbox` (:1295), `test_modal_resume_resets_workspace_readiness_when_sandbox_is_recreated` (:1540), `test_modal_sandbox_create_sets_default_cmd_for_custom_registry_image` (:539), `test_modal_sandbox_create_uses_custom_image_builder_version` (:578), `test_modal_shutdown_rehydrates_sandbox_and_terminates_without_wait_kwarg` (:1755), `test_modal_stop_is_persistence_only_and_shutdown_terminates` (:1711).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "sandbox resume reconnect from_id poll recreate template pause_on_exit shutdown terminate best effort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reconnect-first/probe-policy-aware/recreate-fallback resume ladder and the unconditional state-clearing best-effort shutdown — both port directly to any remote-sandbox or long-lived-remote-resource adapter. Adopt signature-introspected create-kwargs filtering when you must support multiple SDK versions. Adapt the liveness probe to your provider's semantics (poll-None vs is_running) and keep it policy-gated. Omit the image-builder-version process-local override unless your provider has global build-config state. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
