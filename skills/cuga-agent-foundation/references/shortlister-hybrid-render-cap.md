<!-- capsule-v2 -->
# Hybrid shortlist + find_tools render cap — why must the discovery seam's output width be capped separately from the ranker's top_k?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#624/#664); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When a cheap prefilter feeds an expensive reranker, where do failure boundaries live, and why is `max_results=10` enforced in `find_tools` rather than inside any strategy?

## HybridShortlister
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/shortlister/hybrid.py:28-72`; markdown renderer `render.py:50-101` (`render_tools_markdown`) + `_output_schema_for` :22-37; call-site gates `prompt_utils.py:578-653` (`PromptUtils.find_tools`, `engage_cosine` :627, render-cap clamp :649) and `:656-723` (`shortlist_tool_names`, `effective_top_k = min(top_k, plan.top_k)`).
**Signature:** `async shortlist(request) -> ShortlistResult`; `render_tools_markdown(candidates, tools, display_query, notes=None) -> str`.

### Decisive source
```python
# prompt_utils.py:627-650 — two conditions, both required; cap lives at the CALL SITE
engage_cosine = not plan.is_llm_only and len(all_tools) > plan.threshold
if not engage_cosine:
    plan = plan.model_copy(update={"strategy": "llm", "instance": None})
result = await run_shortlister(plan, ShortlistRequest(...,
    top_k=plan.top_k if engage_cosine else None,
    max_results=plan.max_results if engage_cosine else None, ...))
candidates = result.candidates
# Enforce the render cap here rather than inside a strategy: it is a property
# of what find_tools may print, not of how a ranker scores. Applied only when
# the cosine stage is engaged, so the default LLM path keeps its historical
# "no fixed result count" behavior untouched.
if engage_cosine and plan.max_results:
    candidates = candidates[: plan.max_results]
```
```python
# hybrid.py:45-72 — prefilter only when there is something to cut
width = request.top_k or 0
if width and len(pool) > width:
    try:
        prefiltered = await self._embedding.shortlist(
            dataclasses.replace(request, top_k=width,
                                max_results=None))   # cut width governs, not render cap
        narrowed = [by_name[c.name] for c in prefiltered.candidates if c.name in by_name]
        if narrowed:
            pool = narrowed
    except ShortlisterUnavailableError as e:
        logger.warning("... embedding leg unavailable ({}); ranking all {} tools with the LLM", ...)
return await self._llm.shortlist(dataclasses.replace(request, tools=pool))
```

**Flow:** hybrid = embedding prefilters to `top_k` (default 128), LLM reranks that pool and ITS ordering wins; `dataclasses.replace` builds per-leg requests so the shared request never mutates. If cosine is unavailable it degrades to plain LLM over ALL tools (today's behavior, already covered by existing tests). At seam B the caller's provider cap can only be LOWERED by config (`min(top_k, plan.top_k)`), never raised; the historical hallucination filter (dedupe + valid_names + clamp) still runs after ANY strategy as defense-in-depth for custom strategies.

**Invariant:** (1) `max_results`(10) is ignored by strategies and applied only in `find_tools` AFTER ranking — because each rendered tool carries description+reasoning+param docs+both JSON schemas (~400–1500 chars); 128 tools ≈ 50K–190K chars vs `execution_output_max_length` 70K, so an uncapped render would be silently truncated mid-markdown with no error. The bind_cap seam ignores `max_results` entirely (`top_k` IS the cap there). (2) Renderer skips candidate names matching no tool SILENTLY (preserving the original `if not actual_tool: continue`), appends `notes` on BOTH empty and normal branches, and takes `display_query` verbatim from callers so output stays byte-stable. (3) Input/Output Schema blocks are now CONDITIONAL (#644): `input_schema_adds_detail()` walks $ref/$defs/rich-constraint keys recursively and emits JSON only when Parameters prose would lose information; `should_emit_output_schema()` emits Output Schema JSON only when Response Schema text is absent. (4) Prefilter is skipped entirely when `len(pool) <= width` — below the threshold the LLM would see the same set either way.

**Probe:** direct tests `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_shortlister_hybrid.py::test_cosine_narrows_the_pool_before_the_llm_sees_it` (:53), `::test_prefilter_is_skipped_when_the_pool_already_fits` (:64), `::test_llm_ordering_wins` (:77), `::test_degrades_to_plain_llm_when_embeddings_are_unavailable` (:94); schema trim `tests/test_find_tools_schema_trim.py::test_input_schema_adds_detail_false_for_lossy_safe_schemas` (:63) + corpus regression tests `tests/test_schema_trim_public_corpus.py`, `tests/test_schema_trim_appworld_corpus.py`, `tests/test_corpus_loss.py`; seam wiring `tests/unit/test_shortlister_config_surfaces.py::test_configurable_reaches_find_tools_through_run_config` (:65).

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "HybridShortlister render_tools_markdown engage_cosine input_schema_adds_detail", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT the split whenever a cheap recall stage feeds an expensive precision stage: keep the render/presentation cap at the presentation boundary (it belongs to the consumer's budget, not the ranker), let the precision leg own ordering, and degrade to the legacy whole-set path when the cheap leg cannot run.
