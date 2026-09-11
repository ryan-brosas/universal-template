<!-- capsule-v2 -->
# Opik tracing as an LLMTransport decorator — how does one wrapper trace every LLM call with zero per-call-site changes?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter adding observability must know how to trace every LLM call uniformly at the transport choke point, gate tracing with one AND-function both construction paths share, and guarantee tracing can never take down a real LLM call.

## OpikTracingTransport — observe, never alter
**Path/Symbol:** `transport/opik_tracing.py:OpikTracingTransport` (364-517); `wrap_if_enabled` (87-96); `resolve_opik_gate` (99-107); `traced_transport_factory` (110-118); `_guarded_cm` (166-197); `is_opik_configured` (77-84).
**Signature:** `OpikTracingTransport(inner: LLMTransport, *, project_name=None)`; `wrap_if_enabled(transport, *, enabled, project_name=None) -> LLMTransport`; `resolve_opik_gate(enabled_flag: bool) -> bool`; `traced_transport_factory(factory, *, opik_active, project_name=None) -> Callable[[], LLMTransport]`.
**Data Shape:** Decorates any `LLMTransport`, recording one Opik `"llm"` span per `complete`/`complete_structured`/`stream` call. Delegates the actual call to `inner` unchanged — it only observes. `provider`/`model_name` proxy to inner. `_safe_span` yields a real Opik span or a harmless `SimpleNamespace` stand-in if Opik fails at any stage.

### Decisive source
```python
def resolve_opik_gate(enabled_flag: bool) -> bool:
    # ONE AND-gate both ControlPlane.start() and PipesHubAgentFactory.create() call
    return bool(enabled_flag) and is_opik_configured()

def wrap_if_enabled(transport, *, enabled, project_name=None):
    if not enabled:
        return transport
    return OpikTracingTransport(transport, project_name=project_name)

def traced_transport_factory(factory, *, opik_active, project_name=None):
    # wraps a zero-arg factory so the transport it produces is traced
    return lambda: wrap_if_enabled(factory(), enabled=opik_active, project_name=project_name)

@contextlib.contextmanager
def _guarded_cm(build_cm, label):
    try:
        cm = build_cm(); value = cm.__enter__()
    except Exception:
        _logger.debug("Opik %s failed to start; continuing untraced", label, exc_info=True)
        yield types.SimpleNamespace(); return
    try:
        yield value
    except BaseException as exc:
        try: cm.__exit__(type(exc), exc, exc.__traceback__)
        except Exception: _logger.debug(...)
        raise
    else:
        try: cm.__exit__(None, None, None)
        except Exception: _logger.debug(...)
```

**Flow:** `ControlPlane.start()` wraps each transport factory via `traced_transport_factory`/`wrap_if_enabled` at registration time, so every LLM call site (turn loop, planning/critique/route_task, `parse_intent`, `best_of_n`, auto-compact summarizer, `RubricGrader`, `SkillExtractor`) is traced with zero per-call-site changes. Correlation across a whole run comes free from Opik's own contextvar-based `start_as_current_span` — a span nests under whatever trace/span is active in the current asyncio task. `maybe_start_run_trace` opens one trace per ROOT `Agent.run()` (no-op for sub-agents, since Opik can't nest traces); `maybe_start_tool_span`/`maybe_start_agent_span`/`maybe_start_named_span` open `tool`/`general`/custom spans at the tool-executor, `run_child`, and raw-LangChain call sites. `build_langchain_opik_callbacks` returns an `OpikTracer` callback (built fresh per call site, never a module singleton) for the handful of adapter sites that invoke raw LangChain models.
**Invariant:** Tracing must never be able to take down a real LLM call — every Opik SDK call is best-effort (`_guarded_cm`), failures logged at DEBUG, the underlying transport call proceeds untraced. Only exceptions raised by the WRAPPED call propagate. `resolve_opik_gate` is the single source of truth for "is tracing active" so the gate can't drift between `ControlPlane` and the adapter factory. `traced_transport_factory` must build a NEW inner transport each call (no caching).

**Probe:** `tests/unit/agent_loop_lib/transport/test_opik_tracing.py` (pins `resolve_opik_gate` AND-truth table incl. self-hosted `OPIK_URL_OVERRIDE` without API key; `wrap_if_enabled` returns unwrapped when disabled; `traced_transport_factory` builds fresh inner each call; `_guarded_cm` swallows Opik start failure and still propagates real tool exceptions; `OpikTracingTransport` records tool-call/usage on span and survives `opik.start_as_current_span` raising). `tests/unit/agent_loop_lib/runtime/test_runtime_opik.py` (pins `run_child` opens agent span, max-spawn-depth enforced BEFORE opening a span, Opik failure doesn't break child run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "OpikTracingTransport", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "resolve_opik_gate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the decorator-at-the-choke-point pattern (wrap the transport factory, not each call site), the `resolve_opik_gate` single AND-function, the `_guarded_cm` fail-open context manager that can never break the wrapped call, and the fresh-per-call-site LangChain callback (no singleton). Adopt the span taxonomy: `llm` (transport), `tool` (executor), `general` (sub-agent boundary + named spans), one `trace` per root run. Adapt project_name/env gate (`OPIK_API_KEY` OR `OPIK_URL_OVERRIDE`) and span names to host. Omit Opik-specific SDK internals and the legacy LangChain `config={"callbacks":[...]}` pattern (replaced by this uniform wrapper). Direct tests confirm all invariants; index coverage `no_recorded_issue`+`metadata_match` (best-effort caveat).
