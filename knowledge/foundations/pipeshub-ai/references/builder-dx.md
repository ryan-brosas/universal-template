<!-- capsule-v2 -->
# AgentBuilder fluent DX — how do you hide ControlPlaneConfig's full surface behind a chainable builder without creating a second construction path?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does a library consumer get a working agent in one line while every builder method stays a thin setter over the SAME config the CLI constructs by hand?

## Builder → ControlPlane.start() → make_spec() → Agent(spec, runtime)
**Path/Symbol:** `backend/python/app/agent_loop_lib/builder.py` — module docstring (:6-12), `BuiltAgent` (:15-45), `AgentBuilder.build` (:224-242), `create_agent` shortcut (:245-258).
**Signature:** `AgentBuilder().role(r).model(m).api_key(k).transport(t).tools([...]).memory(...).knowledge(...).mode(m).config(**kw).spec_overrides(**kw)` → `await build() -> BuiltAgent`; or `await create_agent(role="coder", model=..., tools=[...])`.
**Data Shape:** `BuiltAgent(agent, control_plane)` bundles the agent with ITS control plane so callers who provisioned sandboxes/SQLite storage have an obvious release path (`close()` / async-context-manager); `__getattr__` delegates everything else to the wrapped agent (`.run`, `.todos`, ...) — non-breaking wrapper, not a new API surface.

### Decisive source
```python
# builder.py:6-12 — the no-second-path rule
"""Every builder method is a thin setter over the same config the CLI
already constructs by hand — nothing here bypasses ControlPlane;
.build() still goes through the exact ControlPlane(cfg).start() ->
make_spec() -> Agent(spec, runtime) pipeline."""
# :224-233
async def build(self) -> BuiltAgent:
    cfg = ControlPlaneConfig(**self._cfg_kwargs)
    control_plane = ControlPlane(cfg)
    await control_plane.start()
    if self._custom_role is not None:
        control_plane.role_registry.register(self._custom_role)
    spec = control_plane.make_spec(self._role_name, **self._overrides)
```

**Flow:** setters accumulate `_cfg_kwargs`/`_overrides` → build() starts ControlPlane (registers custom roles on the fly for library consumers who don't touch the global registry) → make_spec applies overrides (max_turns, output_style, extra_prompt_sections...) → optional `AgentFactory.wire_sub_agents(spec, sub_agents)` → construct Agent → return BuiltAgent. `create_agent` maps dedicated kwargs onto builder methods and passes the rest to `config()`.
**Invariant:** There is EXACTLY one construction pipeline; the builder is syntax over it. Role accepts either a builtin registry name resolved at build time or a live Role instance registered just-in-time.
**Probe:** `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py` (ControlPlane.start→make_spec surface); role resolution exercised via `tests/unit/agent_loop_lib/control_plane/test_skills_pinning.py`; caveat: builder itself has no dedicated unit file — its behavior is pinned through the control-plane coverage suite it funnels into; port with a smoke test asserting `.run()` works after `build()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "AgentBuilder BuiltAgent create_agent make_spec ControlPlaneConfig", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thin-setter builders over one canonical construction pipeline plus the bundled-resource BuiltAgent wrapper; adapt config field names and role registry to host; omit sub-agent wiring unless you need spawn trees from config. Coverage caveat recorded above — no direct builder unit tests upstream.
