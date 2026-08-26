<!-- capsule-v2 -->
# AgentSpec frozen model — what is the minimal immutable definition every producer (roles, factories, builders) must converge on?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What does "an agent" reduce to such that roles/factories/builders/agents-as-tools all just produce it and nothing downstream cares how it was built?

## Layer-0 pydantic spec: prompt + tools + loop + per-agent middleware installers; ModelSpec.resolve is the ONE provider→Model site
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/spec.py:AgentSpec/ModelSpec` (L27–108); consumed by `agent/prompt.py` (Layer 1), `runtime/runtime.py`, `role-factory-wiring` (AgentFactory), builder-dx.
**Signature:** `AgentSpec(name, description, capabilities, system_prompt: Any = str|SystemPromptBuilder, tool_names, pinned_toolsets, tool_disclosure: Literal["eager","lazy"] = "eager", model: ModelSpec, loop: LoopStrategy = ReActLoop(), max_turns=20, mode="act", output_style, prompt_section_order, extra_prompt_sections, middleware: list[Callable[[HookRegistry], None]])`; `ModelSpec(provider, model, thinking_budget, effort).resolve(registry) -> TransportModel`; both models carry frozen/arbitrary-types config (`AgentSpec` frozen via arbitrary_types for callables; `ModelSpec` explicitly `frozen=True`).
**Data Shape:** Pure data + two deferred resolutions: system_prompt may be a builder OBJECT resolved per turn; middleware are INSTALLER CALLABLES applied once at Agent binding.

### Decisive source
```python
class ModelSpec(BaseModel):
    """Immutable — swapping models means building a new ModelSpec, never
    mutating one shared across agents."""
    model_config = {"frozen": True}

    def resolve(self, registry):
        """...the one place a `provider` string turns into a concrete,
        callable Model instance, keeping Agent itself free of any
        TransportRegistry/LLMTransport knowledge."""

# tool_disclosure docstring — the eager/lazy contract:
# "eager" (default): explicit grant always fully visible from turn 0;
# "lazy": tool_names becomes a PERMISSION CEILING rather than an eager
# grant — visibility starts at essentials/pinned toolsets and only grows
# via fetch_tools/search_tools/preloading, never beyond tool_names. Only
# takes effect when the registry actually has toolsets (has_toolsets()).
```

**Flow:** producers (Role data → AgentFactory; Builder DSL; agent_as_tool composition) all emit an AgentSpec → binding applies each middleware installer ONCE against the shared kernel (installers own their idempotency — several agents share one runtime's kernel) → per turn, spec drives prompt construction, loop shape, disclosure mode, and model resolution.
**Invariant:** (1) Everything in the framework exists to PRODUCE a spec; nothing downstream needs to know how — any new agent feature must land as spec DATA, not a new producer pathway. (2) `middleware` travels WITH the spec (per-agent deterministic behavior, e.g. a sub-agent that always forces critique) as opposed to ControlPlane-level hooks; installer idempotency is the installer's job. (3) lazy disclosure narrows but never widens the named-tool ceiling, and silently degrades to eager on flat registries. (4) ModelSpec immutability keeps cross-agent model sharing safe.
**Probe:** No dedicated test_spec.py at HEAD — caveat recorded. Specs exercised throughout `tests/unit/agent_loop_lib/agent/*` (spawn dependencies :1+, plan-execute, opik integration) and adapter support factory `tests/unit/agents/adapter/support/agent_factory.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "AgentSpec ModelSpec resolve tool_disclosure middleware", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-data Layer-0 contract with deferred builder/middleware/model resolutions when designing any agent definition surface. Adapt field set to host capabilities. Omit nothing portable — the discipline IS the content. Coverage caveat: direct unit tests absent; behavior pinned indirectly by every agent-loop integration test.
