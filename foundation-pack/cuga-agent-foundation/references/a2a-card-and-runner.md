<!-- capsule-v2 -->
# A2A agent card + runner selection — pure-function capability advertisement and lazy double-checked supervisor creation

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You expose an agent over a discovery protocol (agent card at `/.well-known/agent.json`) and must pick between multiple backing runners by configuration. How do you keep the card buildable in tests with zero I/O, and how do you avoid paying heavyweight init cost for deployments that enable the endpoint but never receive a request?

## The card builder
**Path/Symbol:** `src/cuga/backend/server/a2a/agent_card.py` (`build_agent_card` :40-69, `_coerce_skill` :20-37); `src/cuga/backend/server/a2a/runner.py` (`SupervisorA2ARunner._ensure_supervisor` :60-75, `run` error shaping :87-105, `PlaceholderA2ARunner` :108-123, `build_a2a_router_for_settings` :143-174).
**Signature:** `build_agent_card(settings: Mapping, skills: Sequence[Mapping]) -> AgentCard`; `_ensure_supervisor() -> supervisor`.
**Data Shape:** skills coerce from loose mappings — missing display fields fall back to the skill id so output always round-trips the SDK's pydantic model; security_schemes emit a bearer/JWT scheme only when `auth_required`.

### Decisive source
```python
# runner.py:60-68 — lazy + double-checked: check OUTSIDE the lock too
existing = getattr(self._app_state, "a2a_supervisor", None)
if existing is not None:
    return existing
async with self._lock:
    existing = getattr(self._app_state, "a2a_supervisor", None)
    if existing is not None:
        return existing
    supervisor = await CugaSupervisor.from_yaml(self._yaml_path)  # lazy import
    self._app_state.a2a_supervisor = supervisor
```
```python
# runner.py:99-105 — leak-proof error surface on the wire
except Exception as exc:
    logger.exception("A2A inbound delegation failed")   # full traceback → logs only
    yield A2AStreamEvent("error",
        {"text": f"A2A handler error: {type(exc).__name__}"},   # class name → caller
        final=True)
```

**Flow:** runner selection ladder in `build_a2a_router_for_settings`: `supervisor_config_path` set → SupervisorA2ARunner; else an event_stream_func provided → SimpleA2ARunner (with auto_approve flag); else PlaceholderA2ARunner whose terminal event explains the missing config — the endpoint ALWAYS answers with a well-formed Task envelope instead of HTTP 5xx. Settings projection goes through `getattr` with defensive defaults (accepts Dynaconf blocks and plain test dicts alike).
**Invariant:** the card builder is a PURE function (no I/O) so any test can construct a valid card; heavy supervisor init happens on first request under a lock checked on BOTH sides (the pre-lock check keeps the hot path free of lock acquisition); concurrent first-requests serialize into exactly one build. Error text carries only the exception CLASS name — tracebacks go to operator logs, never the wire.

**Probe:** direct tests `tests/unit/a2a/test_agent_card.py::test_agent_card_validates_against_a2a_sdk_types` (:80), `::test_agent_card_security_schemes_when_auth_required` (:92), `::test_agent_card_no_security_when_auth_off` (:100), `::test_agent_card_skill_ids_are_stable` (:64); `tests/integration/a2a/test_a2a_router.py` + `test_simple_runner.py` for router selection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "build_agent_card SupervisorA2ARunner _ensure_supervisor PlaceholderA2ARunner build_a2a_router_for_settings", limit: 10 });
```

## Verdict
Adopt pure-function capability cards with id-fallback coercion, lazy double-checked heavyweight init cached on app state, exception-class-name-only error surfaces, and a placeholder runner that keeps unconfigured endpoints protocol-valid. Adapt the card fields and settings keys to your protocol version. Omit auth schemes unless your deployment fronts real traffic.
