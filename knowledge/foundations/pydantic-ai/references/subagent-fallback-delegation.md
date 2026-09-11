<!-- capsule-v2 -->
# Subagent fallback delegation — how a local tool wraps a native capability via a one-shot subagent, with sync/async model resolution

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When the outer agent's model lacks a native capability (X search, image generation), what is the contract for delegating to a subagent that HAS it — including per-run model resolution and error mapping?

## `XSearchSubagentTool` + `ImageGenerationSubagentTool` (+ `_IMAGE_ONLY_MODELS` guard)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/common_tools/x_search.py:XSearchSubagentTool.__call__` (:44–66), factory `x_search_tool` (:69–100); `common_tools/image_generation.py:ImageGenerationSubagentTool.__call__` (:96–131), `_check_image_only_model` (:47–56), `_IMAGE_ONLY_MODELS` table (:38–45). Shared type: `FallbackModelFunc = Callable[[RunContext], Awaitable[Model|str] | Model | str]`.
**Signature:** `async def __call__(self, ctx: RunContext[Any], query_or_prompt: str) -> str | BinaryImage`.
**Data Shape:** Tool dataclass holds `model: Model | KnownModelName | str | FallbackModelFunc`, the configured `native_tool`, fixed `instructions`. Callable resolution supports sync return, async return, or awaitable — strings resolve to models at call time.

### Decisive source
```python
# x_search.py:55-66 — the delegation body (image twin differs in output type + guard)
model = self.model
if callable(model):
    result = model(ctx)
    if inspect.isawaitable(result):
        result = await result
    model = result
agent = Agent(model, output_type=str,
              capabilities=[NativeTool(self.native_tool)],
              instructions=self.instructions)
try:
    result = await agent.run(query)
except UnexpectedModelBehavior as e:
    raise ModelRetry(str(e)) from e
return result.output
```

**Flow:** outer model lacks native support → tool call → resolve fallback model (per-run callable allowed; image path additionally re-checks dynamically resolved STRINGS against the image-only table at call time — static strings were validated at factory time) → build a fresh single-purpose Agent carrying ONLY the native tool → run once → map failure.

**Invariant:** Subagent failure (`UnexpectedModelBehavior`) maps to `ModelRetry`, so the OUTER model gets a corrective prompt instead of the run dying — delegation errors are the caller's retryable input problem. The image-only guard exists because dedicated image models can't host the conversational Agent loop the delegation requires; it raises UserError naming a suggested conversational replacement (e.g. `'gpt-image-1' → 'openai-responses:gpt-5.4'`). Each call constructs a fresh Agent — no shared session state leaks between delegations.

**Probe:** `tests/test_x_search.py` / `tests/test_image_generation.py` pin the callable-resolution matrix and the ModelRetry mapping; `tests/test_image_generation.py` covers `_check_image_only_model` for static and dynamic resolution paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "x_search_tool image_generation_tool XSearchSubagentTool ImageGenerationSubagentTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sync/async/awaitable model-resolution ladder and the UnexpectedModelBehavior→ModelRetry mapping for any "capability the host model lacks" delegation. Adapt the guard table to your own non-conversational model families. Omit the specific xAI/image vendor wiring.
