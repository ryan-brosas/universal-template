<!-- capsule-v2 -->
# Shared execution-feedback constant + warm-up contracts — why must consumers of message text import the producer's constant, and when does boot-time warming beat lazy loading?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#695/#664 follow-ups); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Three consumers matched the literal `"Execution output:"` prefix to detect execution history — how do you stop that string from drifting, and which components must warm at boot instead of lazily?

## EXECUTION_OUTPUT_PREFIX + shared fastembed session + catalogue warm
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/graph/graph_nodes.py:219-231` (`EXECUTION_OUTPUT_PREFIX = "Execution output:"`, `execution_output_text`); consumers rewritten: `shared_nodes.py:336` (reasoning-only finalize fallback), `adapter/response_utils.py:24` (`reflection_current_task`), `adapter/graph_adapter.py:241` (`_any_execution_ran`); shared ONNX session `storage/embedding/embedding_service.py:133-155` (`get_shared_text_embedding`, `_create_local` now delegates); server warm `server/main.py:210-232,1137-1141` (`warm_shortlister_catalogue` in lifespan).
**Signature:** `execution_output_text(output) -> f"{EXECUTION_OUTPUT_PREFIX}\n{output}"`; `get_shared_text_embedding(model_name)` raises whatever fastembed raises; `async warm_shortlister_catalogue(agent_id=None) -> int`.

### Decisive source
```python
# graph_nodes.py:220-225 — the comment IS the contract
# Prefix of every execution-feedback HumanMessage. Consumers that *detect*
# execution history by matching message text (Lite's blocked-claim evidence,
# the reasoning-only finalize fallback, reflection task extraction) must use
# this constant so they cannot drift from the producer below.
EXECUTION_OUTPUT_PREFIX = "Execution output:"
```
```python
# main.py:210-226 — warm-up is an optimization: never fail boot over it
async def warm_shortlister_catalogue(agent_id=None) -> int:
    """Embed the current tool catalogue for cosine shortlisting. ... 0 when the
    default LLM strategy is configured ... Deliberately swallows everything:
    neither boot nor a tools update should fail because an embedding model is
    unavailable."""
    try:
        provider = ToolRegistryProvider(agent_id=agent_id)
        tools = await provider.get_all_tools()
        return await warm_tool_vectors(tools)
    except Exception as e:
        logger.warning(f"Shortlister catalogue warm-up skipped: {e}")
        return 0
```

**Flow:** SDK mode stays LAZY (background load + unavailable-degrade is right for a library); SERVER mode warms in lifespan because "the first find_tools after boot silently falling back to the LLM would be a visible regression" — and only when a cosine strategy is configured (`warm_tool_vectors` returns 0 for llm-only plans, so default deployments pay nothing). `get_shared_text_embedding` extracts the get-or-create fastembed session from `_create_local` so knowledge, policy AND shortlister share one ONNX session per model ("two sessions double memory and load time"); it honors `FASTEMBED_CACHE_PATH` + `HF_HUB_OFFLINE` for air-gapped preload.

**Invariant:** (1) Text-matching detection MUST reference the producer constant — three separate consumers had copied the literal, and any wording change would have silently broken blocked-claim evidence, finalize fallback, and reflection extraction at once. (2) Boot-time warming is for servers with user-visible first-query latency; lazy+degrade is for SDK/library callers where a one-call fallback is invisible. Warm paths NEVER raise. (3) One embedding session per model per process — new embedding consumers must call `get_shared_text_embedding`, not construct `TextEmbedding` directly.

**Probe:** direct tests `tests/unit/test_e2e_server_stack.py` + `src/system_tests/e2e/server_stack.py` (lifespan wiring); `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_shortlister_warm.py::test_*` (warm counts, cache misses only); shared-session pinned by `tests/unit/` embedding-service suites asserting `_embedding_model_cache` reuse across knowledge/policy/shortlister construction.

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "EXECUTION_OUTPUT_PREFIX get_shared_text_embedding warm_shortlister_catalogue", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT both patterns together when adding an embedder-backed feature to a platform that already has one: route through the shared session getter, and give each consumer an explicit lazy-vs-warm answer based on who pays the latency.
