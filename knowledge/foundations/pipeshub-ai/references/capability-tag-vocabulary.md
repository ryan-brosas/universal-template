<!-- capsule-v2 -->
# Capability tag vocabulary — how does dispatch stay name-agnostic when adding spawn-like/terminal-like tools?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do the turn loop, runtime, and middleware recognize CAPABILITIES ("this ends the run", "this spawns children") without hardcoding tool names?

## Six TAG_* constants; dispatch asks has-tag, never is-name
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/tags.py:TAG_SPAWN/TAG_SPAWN_BATCH/TAG_LIFECYCLE_TERMINAL/TAG_DEDUP_EXACT/TAG_PLANNING_CREATE_PLAN/TAG_UI_ONLY` (L43–82); consumers `agent/__init__.py:862–924` (batch partition), `agent/tool_loop.py:71–81` (dedup), `runtime/runtime.py:175–191` (UI strip), `tools/builtin/web/web_scrape.py` (opt-in dedup).
**Signature:** `TAG_SPAWN_BATCH = Tag("spawn", "batch")`; effective tags = owning toolset tags merged with the tool's own (`ToolRegistry.tags_for_name` / `tags_for`).
**Data Shape:** Any host tool opts in by including a tag constant in its `tags` property — no registration step.

### Decisive source
```python
# Narrower than TAG_SPAWN: a call that must be pre-launched as an independent
# asyncio.Task via schedule_spawn_batch BEFORE the turn's non-spawn calls run.
# Only SpawnAgentTool carries this one; BestOfNTool schedules its own
# candidates internally and must NOT be pulled into that batch, so it gets
# TAG_SPAWN without TAG_SPAWN_BATCH.
TAG_SPAWN_BATCH = Tag("spawn", "batch")

# A tool that talks directly to the top-level HUMAN user... Meaningful only
# for the agent the human is actually watching — run_child() strips every
# TAG_UI_ONLY tool from a spawned child's grant UNCONDITIONALLY (regardless
# of depth): a child's "question" has nowhere to go (no UI surface watching
# its own turns) and no way back into the parent's turn loop, so granting it
# one just gives the model a way to stall a whole spawn tree waiting on an
# answer nobody will ever provide.
TAG_UI_ONLY = Tag("interaction", "ui_only")
```

**Flow:** agent `step()` partitions calls by `TAG_SPAWN_BATCH in registry.tags_for_name(c.name)` (pre-launched batch vs parallel wave) → dedup gate keys on `TAG_DEDUP_EXACT` → terminality resolved via `TAG_LIFECYCLE_TERMINAL` + the tool's own `extract_outcome()` → child grants filtered by `TAG_UI_ONLY`, spawn tools stripped one hop from depth limit via `TAG_SPAWN`.
**Invariant:** (1) Dispatch sites ask "does this tool have tag X", never "is this tool named Y" — adding a new spawn-like or terminal-like tool requires ZERO edits to loop/runtime/guards. (2) The SPAWN-vs-SPAWN_BATCH distinction is load-bearing: collapsing them drags best_of_n into the pre-launch batch it must own privately. (3) UI-only tools are a CATEGORY error for children, not a resource issue — hence unconditional stripping at every depth. (4) Constants live centrally: grep-a-tag finds all consumers; a typo is one fix, not N drifting literals.
**Probe:** Indirect through consumer suites: spawn batch partition pinned by integration tests `test_spawn_agent_detach/direct_dispatch` + planner suites driving `agent/__init__.py:862–924` (see spawn capsules); no direct test file for `tags.py` itself — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "TAG_SPAWN TAG_SPAWN_BATCH TAG_LIFECYCLE_TERMINAL TAG_UI_ONLY tags_for_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capability-tag vocabulary + tag-keyed dispatch for any extensible tool surface with loop-level behaviors; adapt tag names. Omit PipesHub's specific builtin assignments. Coverage caveat: constants tested transitively through dispatch consumers only — port alongside those tests.
