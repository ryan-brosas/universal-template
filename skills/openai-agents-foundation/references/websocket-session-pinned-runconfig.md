<!-- capsule-v2 -->
# WebSocket session pinned run-config — how do many Runner calls share one warm websocket provider without letting callers fork the routing config?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How do you pin every run (and nested agent-as-tool runs) to a single websocket-capable provider while preserving prefix-based model routing?

## Identity-checked frozen session
**Path/Symbol:** `src/agents/responses_websocket_session.py:` `ResponsesWebSocketSession` (:23–86), factory `responses_websocket_session` (:89–139), `_validate_provider_alignment` (:42–52), `_prepare_runner_kwargs` (:58–66).
**Signature:** `run(starting_agent, input, **kwargs) -> RunResult`; `run_streamed(...) -> RunResultStreaming`; `aclose() -> None`; factory params incl. `openai_prefix_mode`, `unknown_prefix_mode`, `responses_websocket_options`.
**Data Shape:** frozen dataclass `{provider: OpenAIProvider, run_config: RunConfig}`; `__post_init__` coerces a dict run_config via `_coerce_run_config` then validates; the context manager yields the session and closes in `finally`.

### Decisive source
```python
def _validate_provider_alignment(self) -> MultiProvider:
    model_provider = self.run_config.model_provider
    if not isinstance(model_provider, MultiProvider):
        raise TypeError("...must be a MultiProvider.")
    if model_provider.openai_provider is not self.provider:
        raise ValueError("...provider and run_config.model_provider are not aligned.")
    return model_provider

def _prepare_runner_kwargs(self, method_name, kwargs):
    self._validate_provider_alignment()
    if "run_config" in kwargs:
        raise ValueError(f"Do not pass `run_config` to ResponsesWebSocketSession.{method_name}().")
    runner_kwargs = dict(kwargs)
    runner_kwargs["run_config"] = self.run_config
    return runner_kwargs
...
finally:
    await session.aclose()
```

**Flow:** factory builds `MultiProvider(openai_use_responses=True, openai_use_responses_websocket=True, …)` → takes `model_provider.openai_provider` as THE shared provider → wraps both in the frozen session → each `run`/`run_streamed` re-validates alignment by OBJECT IDENTITY, rejects caller-supplied `run_config`, injects the session's own, and delegates to `Runner` → `aclose()` closes the provider's cached models (websocket connections included) exactly once at context exit.
**Invariant:** there is exactly one RunConfig and it is not overridable per call — warm websockets and prefix routing (`openai/gpt-4.1` → stripped or preserved model id depending on prefix modes) survive across turns and nested agent-as-tool runs only because they all inherit this same object; alignment is re-checked per call so a mutated/foreign pair fails loud before any request.
**Probe:** `tests/models/test_responses_websocket_session.py::test_responses_websocket_session_run_injects_run_config` (:128 asserts `captured["kwargs"]["run_config"] is ws.run_config`), `::test_responses_websocket_session_preserves_openai_prefix_routing` (:50 asserts `"gpt-4.1"` reaches get_model), `::test_responses_websocket_session_rejects_run_config_override` (:152), `::test_responses_websocket_session_context_manager_closes_provider` (:161).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "responses_websocket_session.py", limit: 24 });
await mcp.codebase_memory.check_index_coverage({ project: "openai-agents-python", paths: ["src/agents/responses_websocket_session.py", "tests/models/test_responses_websocket_session.py"] });
```

## Verdict
Adopt the frozen-session + identity-alignment + override-rejection trio for any long-lived transport sharing (websockets, HTTP/2 sessions); adopt dict→RunConfig coercion with loud unknown keys. Adapt which options the factory exposes. Omit sync-run exposure deliberately (the source has no `run_sync`) if your transport is async-only. Coverage: no_recorded_issue @ gen 2026-08-24T14:05:06Z.
