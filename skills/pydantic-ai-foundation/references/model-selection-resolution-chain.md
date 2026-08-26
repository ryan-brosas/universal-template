<!-- capsule-v2 -->
# Model selection & resolution capabilities — per-step SelectModel, None-falls-through ResolveModelId, and NativeTool spec validation

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/select_model.py` + `resolve_model_id.py` + `native_tool.py` + `_deferred_capabilities.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Where do per-step model choice and string→model resolution hook into the run, and what does "return None" mean in each chain? A porter will make resolvers authoritative when they should be consultative and miss the pre-definition tool-recording step for deferred loads.

## Path / Symbol
`select_model.py` — `SelectModel` dataclass (:10–26): `selector: ModelSelector`, `get_model() → selector` (per LOGICAL model request step; receives ModelSelectionContext w/ deps/history/usage/lower-precedence model). `resolve_model_id.py` — `ModelIdResolver` union (:12–15), `ResolveModelId.resolve_model_id → await_maybe(resolver(ctx, model_id))` (:30–36). `native_tool.py` — `NativeTool.get_native_tools → [self.tool]` (:32–33), module-level `_NATIVE_TOOL_ADAPTER = pydantic.TypeAdapter(AbstractNativeTool)` (:14), `from_spec` flat-vs-explicit YAML forms (:36–52). `_deferred_capabilities.py` — `record_loaded_capability_tools(ctx, request_context)` (:16–33).

## Signature
```python
async def resolve_model_id(self, ctx: ModelResolutionContext[AgentDepsT], *, model_id) -> Model | None
def record_loaded_capability_tools(ctx, request_context) -> ModelRequestContext
```

## Data Shape
Resolver contract: return a Model to claim the ID, or `None` to DEFER to later capabilities / default `infer_model`. Selector may be sync or async and returns a model instance OR a model ID (strings re-resolved downstream). Deferred-load recording emits one `ModelRequest(parts=[ToolAvailabilityDeltaPart(tools_added=sorted_names)])` appended to request_context.messages, updates BOTH `ctx.discovered_tool_names` AND `model_request_parameters.revealed_tool_names` (replace-copy of frozen params).

### Decisive source
The consultative resolver + recording side-effect (`_deferred_capabilities.py` :21–32):
```python
newly_loaded = [tool_def for name, tool_def in loaded.items() if name not in ctx.discovered_tool_names]
if not newly_loaded: return request_context
newly_loaded = sorted(newly_loaded, key=lambda tool_def: tool_def.name)
tools_added = [tool_def.name for tool_def in newly_loaded]
request_context.messages.append(ModelRequest(parts=[ToolAvailabilityDeltaPart(tools_added=tools_added)]))
ctx.discovered_tool_names.update(tools_added)
... revealed_tool_names=... | set(tools_added)
```

**Flow:** Resolution chain: model instances skip resolvers entirely; strings walk capabilities first-non-None-wins then fall to infer_model; per-run overrides invoke resolvers too. Selection: `get_model()` is consulted per logical request step so mid-run model switching works (deps/usage-aware). NativeTool.from_spec validates via the pydantic TypeAdapter against the AbstractNativeTool discriminated union (flat `{kind: web_search, ...}` kwargs or explicit `{tool: {...}}`). After deferred capability loads, the delta part records WHAT became available and WHEN in history (sorted by name; deduped against discovered set so long trajectories don't duplicate deltas).

**Invariant:** Resolver None = "I decline, ask someone else"; never raise for unknown ids you don't own. Tool-availability deltas are append-only history events — they persist across turns so later requests see consistent availability timelines.

**Probe:** `tests/test_capabilities.py` — resolve-model-id family (:16402 maps string→model, :16411 None falls through to infer_model, :16422 None for unknown string, :16430 first-non-None-wins, :16449 skipped-for-instance, :16460 invoked-on-override); select-model :9546 first-step deps; deferred delta pins :4239/:4455 (delta persists/not duplicated over long trajectory); wrapper delegation :13607.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ResolveModelId SelectModel record_loaded_capability_tools ToolAvailabilityDeltaPart'
```

## Verdict
**Adopt** consultative-first-non-None-wins resolution chains and per-step model selection via get_model hooks. **Adopt** sorted, deduped, history-recorded availability deltas for any lazily-loaded tool surface. **Adapt** the TypeAdapter-from_spec pattern for your own spec-driven unions.
