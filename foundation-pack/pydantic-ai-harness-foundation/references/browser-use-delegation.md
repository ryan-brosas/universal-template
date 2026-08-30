<!-- capsule-v2 -->
# BrowserUse delegation — a capability that hands open-ended web tasks to an autonomous browser-use agent with a factory seam and shielded teardown

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness expose one `browse_web` tool that runs a full browser-use agent per task, with session scoping, secret redaction, and teardown that survives cancellation?

## BrowserUse capability + BrowserUseToolset
**Path/Symbol:** `pydantic_ai_harness/browser_use/_capability.py` (`BrowserUse(AbstractCapability)`), `_toolset.py` (`BrowserUseToolset(FunctionToolset)`, `BrowserTask`, `BrowserAgentFactory`, `default_browser_agent`, `_kill`), `_model.py`, `_settings.py`.
**Signature:** `BrowserUse(llm=None, browser_profile=None, allowed_domains=None, block_ip_addresses=True, headless=None, max_steps=50, use_vision=True, output_schema=None, sensitive_data=None, session_scope='call'|'agent', cdp_url=None, ...)`.
**Data Shape:** one tool `browse_web(task) -> str`. Session scopes: `'call'` = fresh session per call, killed on end; `'agent'` = one shared `keep_alive` session serialized by a lock, closed for good by `aclose()`.

### Decisive source
```python
# _kill(): BrowserSession.kill is not a single round-trip (saves storage state,
# dispatches a stop event, drains the event bus) so it suspends several times
# over CDP. Unshielded, the first await inside a cancelled scope raises and
# leaves a live Chromium behind. Wrapped in anyio.CancelScope(shield=True) with
# move_on_after(_TEARDOWN_TIMEOUT=30); failures are swallowed so a raise in a
# finally does not replace the unwinding error. Failed sessions are retained
# for a later cleanup attempt.
# _run_in_shared_session: on BaseException the shared session is killed so the
# next call starts fresh; after aclose(), a queued call raises RuntimeError
# rather than lazily starting a browser nothing would close.
# _validate_sensitive_data: flat secrets require a non-empty allowlist with
# explicit hostnames (no wildcard); domain-scoped nested values otherwise.
```

**Flow:** `browse_web` → build session (merge profile + capability overrides, localhost-blocking) → build agent via `BrowserAgentFactory` (default = real `browser_use.Agent`, `enable_signal_handler=False`) → run loop → render result (schema JSON or failure report). `_render_answer` raises `ModelRetry` when structured output fails to parse.
**Invariant:** the factory must not start/stop the session (`browse_web` owns the lifecycle); teardown is shielded and bounded so a browser that will not close is retained, never wedging the caller; secrets stay out of `repr()` and the sub-agent's model.
**Probe:** `tests/browser_use/test_browser_use.py` (fake `BrowserAgentFactory` + `BrowserAgentHistory`) pins session scoping, localhost blocking, result rendering, and teardown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "BrowserUseToolset browse_web BrowserAgentFactory _kill", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the factory seam, session-scope model, shielded teardown, and secret-redaction rules; adapt the browser-use version pin and safe-tools restriction (`_safe_tools` excludes `read_file`/`upload_file` pending pypdf 6.14.2); omit host-specific browser profiles.
