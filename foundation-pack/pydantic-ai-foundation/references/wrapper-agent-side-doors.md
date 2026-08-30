<!-- capsule-v2 -->
# Wrapper agent — transparent delegation and the two realtime side-door overrides

## Source / Question
`pydantic_ai_slim/pydantic_ai/agent/wrapper.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A policy wrapper (auth gate, audit layer) delegates `iter()` to the wrapped agent — but which OTHER entry points silently bypass an `iter()`-only override, and how does the wrapper forward `override()` without clobbering unset fields? A porter will gate only `iter()` and leave realtime sessions and signaling unguarded.

## Path / Symbol
`agent/wrapper.py` — `WrapperAgent(AbstractAgent)` (:52–464), `_resolve_realtime_session` (:320–360), `_open_realtime_session` (:362–407), `override()` (:409–465).

## Signature
```python
class WrapperAgent(AbstractAgent[AgentDepsT, OutputDataT]):
    def __init__(self, wrapped: AbstractAgent[AgentDepsT, OutputDataT]): self.wrapped = wrapped
    # every property/method forwards to self.wrapped verbatim
    async def _resolve_realtime_session(self, model, *, ...) -> AsyncGenerator[_RealtimeSessionResolution]
    async def _open_realtime_session(self, model, *, ...) -> AsyncGenerator[RealtimeSession]
    def override(self, *, name=_utils.UNSET, deps=..., ..., spec=None) -> Generator[None]
```

## Data Shape
Every config surface (model/name/description setters+getters, deps_type, output_type, toolsets, root_capability, event_stream_handler, `__aenter__/__aexit__`, output_json_schema, system_prompt_parts) forwards 1:1. `override()` takes UNSET-sentinel params and forwards only set values; a set `retries` is moved into `forward_kwargs` so it reaches the inner override as its own keyword.

### Decisive source — the documented side-door contract (:337–343, :385–387)
```python
"""Resolve realtime configuration on the wrapped agent.

This backs the WebRTC signaling helpers (`answer_webrtc_offer()` / `create_client_secret()`),
which bake the wrapped agent's instructions and tools into a provider call or browser
credential without opening a session — so a wrapper that gates realtime by overriding
`_open_realtime_session` (see its note below) must also override this method to gate
signaling."""
...
"""Note that realtime sessions do not route through `iter()` (there is no graph run to
iterate), so a wrapper that enforces policy by overriding `iter()` must also override this
method to gate realtime sessions."""
```

**Flow:** Normal runs: caller → wrapper.iter → wrapped.iter. Realtime: TWO extra paths — `_resolve_realtime_session` (signaling: bakes instructions/tools into a WebRTC offer answer or client secret WITHOUT opening a session) and `_open_realtime_session` (the actual session). Both forward verbatim in the base wrapper; policy wrappers must override both or their gate has holes. The override() forwarder passes ALL sentinel params through and lets the inner agent decide what's set — never filter at the outer layer with None checks.

**Invariant:** Delegation must be complete and transparent: any field the wrapper fails to forward becomes an invisible divergence between wrapped and wrapping agents. Policy enforcement points are {iter, _open_realtime_session, _resolve_realtime_session} — a secure wrapper covers all three; signaling is reachable without ever opening a session.

**Probe:** `tests/test_public_interface_contracts.py` guards AbstractAgent/WrapperAgent surface parity; `tests/realtime/test_webrtc.py` + `tests/realtime/test_session.py` exercise the side-door paths through wrappers.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'WrapperAgent _open_realtime_session _resolve_realtime_session override'
```

## Verdict
**Adopt** the three-enforcement-point map as a security invariant for any host that wraps agents. **Adopt** UNSET-sentinel forwarding for override-style CMs. **Adapt** the property list to your AbstractAgent surface. **Omit** the docstring examples (product docs).
