<!-- capsule-v2 -->
# Context-window resolution — how a harness turns a model id into a real token budget (fractions, not constants)

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a compaction strategy know the real context window of the model it is about to run, so a single setting behaves correctly across a fleet of models?

## Window resolution: fractions over constants
**Path/Symbol:** `pydantic_ai_harness/compaction/_context_window.py` (72L) — `resolve_context_window`, `DEFAULT_CONTEXT_WINDOW`.
**Signature:** `resolve_context_window(model: Model | KnownModelName | str | None) -> int | None`; `DEFAULT_CONTEXT_WINDOW = 200_000`.
**Data Shape:** returns the model's real window in tokens, or `None` for unknown. `None` is returned BOTH for unlisted models AND for registry entries without a recorded window, so callers cannot mistake unknown for a number. Zero/negative registry values are treated as absent rather than propagating a budget no request could fit under.

### Decisive source
```python
# The module docstring states the philosophy: every strategy triggers on an
# absolute token budget, but "that constant is wrong for every model it was not
# measured against." So resolve_context_window(model) looks up the REAL window
# via genai-prices (already a transitive dependency) and strategies accept a
# FRACTION instead.
DEFAULT_CONTEXT_WINDOW = 200_000  # deliberately CONSERVATIVE:
# "compacting earlier than necessary costs one summary; overestimating the
# window costs the whole request."
```

**Flow:** strategies accept a fraction of the resolved window. Three-override ladder per strategy: `context_window` (applies always — for registries that are confidently wrong), `fallback_context_window` (only when resolution fails — local endpoints, Bedrock prefixes), else the resolved value. `FallbackModel` reports a composite `fallback:...` id matching no registry entry → resolves to `None` by design.
**Invariant:** unknown must read as `None`, never a number; an over-estimate is worse than an early summary. The module names itself the SINGLE switch point for when pydantic-ai core grows a native window field (upstream issue #4538 referenced).
**Probe:** `tests/compaction/test_context_budget.py` (1,455L) pins window resolution across models and the override ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "resolve_context_window DEFAULT_CONTEXT_WINDOW", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fractions-over-constants with a named fallback ladder and `None`-for-unknown; adapt the `genai-prices` lookup source; omit host-specific model registry entries. Direct test pins resolution; no coverage caveat.
