<!-- capsule-v2 -->
# Remote variable provider lifecycle — how do SSE-push + polling-fallback keep config fresh without thundering re-resolve?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How does the provider thread start/stop, what are the SSE/polling roles, and what auth constraints apply?

## LogfireRemoteVariableProvider (remote.py) + wiring
**Path/Symbol:** `logfire/variables/remote.py:LogfireRemoteVariableProvider` (864L, class head `remote.py`) + selection in `config.py:_initialize` (`config.py:1520-1544`) + lazy init (`config.py:1700-1728`).
**Signature:** constructed with `(base_url, token=api_key, options: VariablesOptions, server_response_hook)`; `start(logfire_instance | None)`, `refresh(force=False)`, `shutdown(timeout_millis)`.
**Data Shape:** `VariablesOptions{block_before_first_resolve=True, polling_interval≥10s default 60s, timeout=(10,10), include_resource_attributes_in_context, include_baggage_in_context, instrument, template_mismatch_policy}`.

### Decisive source
```python
# config.py selection:
if self.variables is None:
    self._variable_provider = NoOpVariableProvider()
elif isinstance(self.variables, LocalVariablesOptions):
    self._variable_provider = LocalVariableProvider(self.variables.config)
else:
    # Only API keys can be used for the variables API (not write tokens)
    if not self.api_key:
        raise LogfireConfigError('Remote variables require an API key. ...')
    self._variable_provider = LogfireRemoteVariableProvider(
        base_url=self.advanced.generate_base_url(self.api_key), ...)
...
# configure() tail:
if config.variables is not None:
    config.get_variable_provider().start(logfire_instance if config.variables.instrument else None)
```
Lazy-init path (`get_variable_provider`): after configure() with NO explicit variables option but a LOGFIRE_API_KEY present, a remote provider is created on FIRST ACCESS with default options and started — "Double-check after acquiring lock" guards the race.
Options docstrings state the delivery model: "Polling is only a fallback — all updates are delivered instantly via SSE unless something goes wrong. Must be at least 10 seconds" (enforced in `__post_init__` raising ValueError).
**Flow:** explicit variables= → provider built at initialize → start() spawns the update thread (SSE listen + interval poll fallback); block_before_first_resolve makes the first `.get()` WAIT for a fetch so code never runs on stale defaults; refresh(force=True) re-pulls; shutdown joins within budget; re-configure shuts down the old provider first (`self._variable_provider.shutdown(timeout_millis=200)` before swap).
**Invariant:** Write tokens are NOT accepted for the variables API — a distinct credential class from export. The instrument flag propagates as `logfire_instance=None` to suppress resolution spans rather than post-hoc filtering.
**Probe:** `tests/test_variables/test_remote_provider.py` family — pins fetch/blocking/SSE-recovery behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "LogfireRemoteVariableProvider VariablesOptions block_before_first_resolve polling_interval", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt push-primary/poll-fallback freshness with first-resolve blocking and strict credential separation. Adapt transport (SSE lib) and auth to your backend. Omit local-provider twin only if you don't need offline/test modes.
