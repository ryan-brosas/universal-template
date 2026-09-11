<!-- capsule-v2 -->
# Tool search index split — why is ranking a separate ABC from the registry, and what must an empty query return?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you keep tool search swappable (keyword → embeddings) without letting the index fork the tool catalog?

## ToolIndex ABC ranks a LIVE registry snapshot; KeywordToolIndex adds name-hit bonus on shared token scoring
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/index.py:ToolIndex/KeywordToolIndex/ToolMatch/_score/_tool_haystack` (L31–101); scoring primitives in `core/text_scoring.py:tokenize/keyword_overlap_score`; consumers: `tools/builtin/lazy_toolsets.py::SearchToolsTool`, `tool_preloading`, registry.
**Signature:** `async search(registry: ToolRegistry, query: str, limit=5) -> list[ToolMatch]`; `ToolMatch(summary, relevance: float, toolset: str | None)`; `_tool_haystack(summary) -> (name_tokens, corpus)`; name bonus `+0.5 * (|name∩query| / |query|)`.
**Data Shape:** Haystack = name tokens ∪ short-description tokens ∪ tag key/value tokens; relevance rounded to 3 decimals; `toolset` membership resolved by the INDEX so callers never re-derive it; zero-score hits dropped.

### Decisive source
```python
# The module docstring carries three load-bearing design decisions:
"""...kept separate from ToolRegistry (Single Responsibility, mirroring
modules/providers/skills/index.py's split between SkillStore and SkillIndex)
so a future embedding-backed index ... can be swapped in via DI without
touching the registry, search_tools, or tool_preloading — all three depend
on this ABC, never on a concrete scoring algorithm.

Deliberately query-time only (no rebuild/add_entry/remove_entry ...): a
ToolRegistry already IS the tool catalog's source of truth ... so a
ToolIndex only ever needs to rank against a live registry snapshot, never
maintain its own copy.

...deterministic, no-LLM-call token-overlap scoring shared with skills
search — the same choice Anthropic's own tool-search guidance makes
(description/name QUALITY matters far more than the search algorithm's
sophistication at this scale)..."""

async def search(self, registry, query, limit=5):
    query_tokens = tokenize(query)
    if not query_tokens:
        return []          # empty/whitespace query returns NOTHING, not everything
```

**Flow:** search_tools/preloading call through the ABC with the live registry → tokenize → score every discoverable summary (including provider-backed not-yet-materialized ones) → drop zero scores → sort desc → attach owning-toolset names → top-limit returned.
**Invariant:** (1) No write API on the index — dual catalogs would drift; ranking always against `registry.discover()` at call time. (2) Empty query ⇒ no matches (callers wanting the catalog have list_toolsets). (3) Name tokens kept SEPARATE so exact-name mentions win ties — same convention as FilesystemSkillIndex. (4) All three consumers depend on the ABC, never the concrete scorer. (5) Search RANKS, never grants execution — visibility growth stays governed by lazy-toolsets ceilings.
**Probe:** No dedicated test_index.py at HEAD — caveat recorded. Behavior exercised indirectly via `tests/unit/agent_loop_lib/tools/test_lazy_toolsets.py` (:181 search_tools handle over the funnel; :55 comment documents KeywordToolIndex as one of two scoring paths) and `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_tool_preloading.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ToolIndex KeywordToolIndex ToolMatch keyword_overlap_score", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-only ranking-over-live-registry + empty-query-returns-nothing + name-bonus token scoring for tool/skill search tiers. Adapt scoring weights after measuring host recall. Omit embedding backends until catalog scale demands them. Coverage caveat: indirect pinning only.
