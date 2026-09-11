<!-- capsule-v2 -->
# Drop-in Agent facade — how do you swap a native agent for a foreign core while keeping every public signature, repr, and lifecycle hook?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what does it take for `browser_use.beta.Agent` to pass tests asserting it is indistinguishable from the Python `Agent` (module, qualname, signature, constructor order) while delegating everything to a Rust core?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — class Agent :4236; identity surgery `Agent.__module__ = 'browser_use.agent.service'` :6777 + `_align_browser_use_agent_signatures()` :6781 (copies `__signature__`/`__annotations__` per method from upstream `_PythonAgent`, then fixes hook annotations); protocol handshake `_ensure_sdk_client` :6440 (`runtime.ping` → `sdk_protocol_version == 1` else close+raise); browser-mode ladder `_browser_mode` :6705 (`remote-cdp` → env overrides → cloud → headless default); cleanup ordering `_finalize_run_cleanup` :4981 (unregister signals → stop eventbus → close browser resources → close SDK client unless keep_alive).
**Signature:** `Agent(task, llm=None, browser_profile=None, browser_session=None, browser=None, tools=None, controller=None, …)` — kwargs mirror `_PythonAgent.__init__` order exactly (pinned by test :116).
**Data Shape:** run methods return the same `AgentHistoryList[AgentStructuredOutput]`; `multi_act` serializes non-done batches into an instruction string via `_actions_instruction` (:4212) and re-enters as a follow-up; done-only batches resolve locally through `_done_action_result` (:4185).

### Decisive source
```python
Agent.__module__ = 'browser_use.agent.service'
Agent.__doc__ = None
def _align_browser_use_agent_signatures() -> None:
    from browser_use.agent.service import _PythonAgent
    for name, browser_use_method in vars(_PythonAgent).items():
        ...
        beta_method.__signature__ = inspect.signature(browser_use_method)
        beta_method.__annotations__ = dict(getattr(browser_use_method, '__annotations__', {}))
    try:
        Agent.__signature__ = inspect.signature(_PythonAgent)
# protocol pin BEFORE first use:
ping = await self._sdk_client.call('runtime.ping')
protocol_version = ping.get('sdk_protocol_version')
if protocol_version == 1: return self._sdk_client
... raise BetaAgentError(f'Unsupported browser-use-terminal SDK protocol {protocol_version!r}; expected 1. ...')
```

**Flow:** construction mirrors Python-Agent semantics locally (task enrichment chain: initial-actions → domain constraints → sensitive-data placeholders → available files → JSON schema; URL-in-task extraction adds a navigate action; MessageManager + SystemPrompt built with provider flags) so callers get identical logging/callbacks; `run()` delegates to ONE `agent.run_task`/`agent.run` RPC carrying the whole config, then projects events back into history (sibling capsules); follow-ups reuse `agent_id`/`browser_id` handles; teardown always runs signal-unregister → eventbus stop → resource kill → SDK close in that order.
**Invariant:** identity metadata is part of the API (module/qualname/doc/repr must equal upstream or isinstance-style introspection breaks); an incompatible core version must fail at ping time with remediation text, never mid-run; `done` actions keep LOCAL completion semantics even though all other actions execute remotely.
**Probe:** `tests/ci/test_beta_agent.py:80` `test_beta_agent_class_metadata_matches_browser_use_service_surface`, `:95` generic subscription parity, `:116` constructor signature/order parity, `:3393` `test_beta_agent_rejects_incompatible_sdk_protocol`, `:5953` finalize-cleanup ordering.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_align_browser_use_agent_signatures _ensure_sdk_client runtime.ping sdk_protocol_version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the signature-alignment surgery + ping-time protocol pin + fixed teardown ordering when shimming a compatible-but-foreign engine behind a stable class; adapt the protocol constant and param vocabulary; omit local multi_act emulation if your core accepts batched actions natively.
