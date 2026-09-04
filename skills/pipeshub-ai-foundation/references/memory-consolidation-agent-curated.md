<!-- capsule-v2 -->
# Agent-curated memory consolidation — who decides which memories are stale, and where does the LLM call happen?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you expose memory curation (merge/replace stale entries) to an agent without embedding a hidden summarization model call in the tool layer?

## memory_consolidate = mechanical delete-many + add-one; quality lives entirely in the calling agent
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/builtin/data/memory_tools.py:MemoryReadTool/MemoryWriteTool/MemorySearchTool/MemoryConsolidateTool` (L16–238); provider interface `modules/providers/memory/base.py:MemoryProvider` (`get/add/search/delete/clear`).
**Signature:** consolidate args `memory_ids: list[str]` (ARRAY, required), `summary: str` (required); write args `content` (required) + optional `metadata` STRING (JSON text); search args `query` + optional `top_k` STRING defaulting `"5"`. All tools return `ToolOutput(success=True, …)` — even not-found.
**Data Shape:** Provenance rides metadata: consolidated entry stores `{"consolidated_from": [removed ids]}` and the result payload echoes `{memory_id, consolidated_from}` for auditability.

### Decisive source
```python
# Module docstring is the porting contract:
"""Deliberately 'agent-curated': the model reads what memory_search
returned, writes the consolidated summary as plain text, and this tool
just does the mechanical delete-many + add-one swap. No LLM call happens
inside the tool/hook layer — consolidation quality is entirely the
calling agent's judgment, kept auditable via `consolidated_from`."""

removed = []
for mid in memory_ids:
    existing = await self._memory.get(mid)
    if existing is not None:            # get-before-delete ⇒ missing ids
        await self._memory.delete(mid)  # silently skipped, never an error
        removed.append(mid)
new_id = await self._memory.add(summary, metadata={"consolidated_from": removed})

# Sibling tolerances on read/write paths:
except (json.JSONDecodeError, ValueError): parsed = {}   # bad metadata JSON ⇒ {}
top_k = kwargs.get("top_k") or "5"; int(top_k)           # top_k arrives as STRING
```

**Flow:** agent calls memory_search → reads candidates → authors one distilled summary itself → passes candidate ids + its own text to memory_consolidate → tool verifies each id exists (get-before-delete), deletes survivors, adds the new entry with full provenance, returns new id + actually-removed list → agent reports consolidation to the user with that audit trail.
**Invariant:** (1) No model call inside the tool/hook layer — a porter who "helpfully" summarizes inside the tool breaks the auditability contract and doubles cost. (2) Get-before-delete makes the swap idempotent-safe: missing/stale ids drop out of BOTH the deletion set and the provenance list instead of erroring mid-swap. (3) Read returns `found:false` data, write/search never fail on malformed input (empty-dict metadata coercion) — errors-as-data at the tool boundary per repo convention. (4) `top_k` is declared STRING and coerced via `int()` because the schema layer's ARRAY/STRING vocabulary has no NUMBER type here; passing it through uncoerced crashes the provider.
**Probe:** Registration-level pin only: `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py` registers the memory toolset (no behavior test for consolidate) — coverage caveat recorded. Deterministic probes: graph resolves `MemoryConsolidateTool`; whole-file source read this pass.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "MemoryConsolidateTool memory_consolidate MemoryWriteTool ToolOutput" --detail ids
```

## Verdict
Adopt agent-curated consolidation with in-band provenance (`consolidated_from`) and get-before-delete tolerance; adopt the no-LLM-in-tools rule for curation; adapt the memory_id namespace and metadata schema to host store. Omit nothing portable. Coverage caveat: no direct unit test upstream at pin.
