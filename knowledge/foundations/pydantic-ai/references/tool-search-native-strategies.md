<!-- capsule-v2 -->
# Tool-search native tool — strategy union and the hidden 'custom' value

## Source / Question
`pydantic_ai_slim/pydantic_ai/native_tools/_tool_search.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Tool discovery has three execution planes (provider-server-side, provider-client-executed running OUR callable, fully-local function tool) behind one user-facing `strategy` field — how is the internal `'custom'` mode kept OUT of the public union while remaining settable on the native tool? A porter will expose 'custom' to users or conflate the three planes' wiring.

## Path / Symbol
`native_tools/_tool_search.py` — whole file: strategy type aliases (:46–92), `TOOL_SEARCH_FUNCTION_TOOL_NAME = 'search_tools'` (:95), `ToolSearchTool(AbstractNativeTool)` (:103–156).

## Signature
```python
ToolSearchNativeStrategy = Literal['bm25', 'regex']        # Anthropic server-side; OpenAI rejects these names
ToolSearchLocalStrategy  = Literal['keywords']             # forward-compat single-member scaffold
ToolSearchFunc = Callable[[RunContext, Sequence[str], Sequence[ToolDefinition]],
                          Sequence[str] | Awaitable[Sequence[str]]]
ToolSearchStrategy = Union[ToolSearchFunc, ToolSearchLocalStrategy, ToolSearchNativeStrategy]
# NB: 'custom' NOT in the user union:
class ToolSearchTool(AbstractNativeTool):
    strategy: Literal['bm25', 'regex', 'custom'] | None = None
```

## Data Shape
`strategy=None` (default) = provider's own default native search. Callables are accepted directly from users and the capability internally stamps `strategy='custom'` so adapters wire the client-executed surface (Anthropic: regular function tool + `tool_reference` result blocks; OpenAI: `ToolSearchToolParam(execution='client')`). Tools enter the searchable corpus via `defer_loading` on their ToolDefinition (`with_native='tool_search'`).

### Decisive source (:140–152)
```python
"""* `'custom'`: discovery is performed by a callable on our side; provider adapters
that support a "client-executed" native surface wire that surface up so the model sees a
tool search call rather than a regular function tool. Set automatically by
[`ToolSearch`][pydantic_ai.capabilities.ToolSearch] when its `strategy` is a callable;
users don't pass `'custom'` directly."""
```
Plus the local-fallback name contract (:95–99): `'search_tools'` is BOTH the plain function tool backing keyword discovery on providers with no native surface AND the name model adapters route to for client-executed modes.

**Flow:** capability resolves per-provider plane → server-side: strategy rides the wire as-is → custom: adapter registers our callable under the native surface, results re-formatted as tool_reference blocks → no native support: local `search_tools` function tool instead. Deferred tools stay off the prompt until discovered (companion contracts: `tool-search-corpus.md`, `native-swap-resolution.md`).

**Invariant:** The public union must never contain `'custom'` — it's a framework-internal discriminator derived from "user passed a callable". Named native strategies are provider-gated ('bm25'/'regex' fail loudly on OpenAI). The single-member `'keywords'` Literal exists so users can PIN today's local algorithm against future default changes.

**Probe:** `tests/test_native_tool_search_vcr.py` (cassette-pinned provider behavior); `tests/test_tool_search.py` — `test_tool_search_eval` (:511), `test_tool_search_toolset_filters_deferred_tools` (:604), `test_search_tool_def_description_and_schema` (:626).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ToolSearchTool TOOL_SEARCH_FUNCTION_TOOL_NAME ToolSearchStrategy'
```

## Verdict
**Adopt** the three-plane taxonomy + hidden-internal-value pattern for any capability that can execute provider-side, client-side, or locally. **Adopt** pin-via-Literal for evolving defaults. **Adapt** strategy names to your providers. **Omit** vendor adapter bodies (models/anthropic.py, models/openai.py — provider surface).
