<!-- capsule-v2 -->
# Tool preloading (PRE_AGENT deterministic toolset unlock)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/tool_preloading.py` (whole file, 187L).

## Path/Symbol
- `tool_preloading(*, index=None, preload_threshold=0.75, mention_threshold=0.4, top_k=10)` (:37) — PRE_AGENT factory
- `_best_match_per_toolset(matches)` (:112)
- `_select_toolsets(registry, matches, *, grant, preload_threshold, mention_threshold) -> (unlocked, pointers, unlock_names)` (:128)
- `_render_preload_section(unlocked, pointers)` (:167)

## Signature
Searches the SAME ToolIndex instance the model-facing search tool uses (defaults to a fresh stateless `KeywordToolIndex`) against `ctx.goal.description` BEFORE turn 0.

## Data Shape
Relevance bands per TOOLSET (best tool match represents its set): ≥0.75 → unlock (tools added to `scope.visible_tools`, prompt says "already loaded"); 0.4–0.75 → one-line pointer ("call fetch_tools if relevant"); <0.4 → nothing.

## Decisive source
```python
if spec.tool_names and spec.tool_disclosure != "lazy":
    # Eager grant: every named tool is already fully visible from turn 0 ...
    await next_fn(); return        # no-op by design, never an error
```
Grant ceiling: `names = [n for n in names if n in grant]`; a toolset with nothing left after intersection is dropped entirely — unlocking beyond the grant is structurally impossible.

## Flow
No-op guards: scope None / goal without description / registry without toolsets / eager disclosure / index failure (logged + skipped). Unlocks via `registry.materialize_many(unlock_names)` then widen `scope.visible_tools`; writes/POPS `scope.extra_prompt_sections["preloaded_tools"]` so a stale section from a prior run can't linger.

## Invariant
**Deterministic half of the middleware-vs-tool tradeoff**: list_toolsets/fetch_tools are tools the model MAY call; preloading hands over what relevance search already knows BEFORE the first turn, so no turn is wasted discovering. Defaults favor precision because an unlock grows EVERY subsequent turn's schema payload.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_tool_preloading.py`: band pins :100/:109/:118, grant-ceiling :124/:140, no-op guards :151–176 incl. swallowed search failure, stale-section clearing :186.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["tool_preloading","preload_threshold","visible_tools"]'`

## Verdict
ADOPT as the deterministic twin of lazy-toolsets disclosure (which this foundation already mines): same relevance-band grammar as skill preloading, applied to tools.
