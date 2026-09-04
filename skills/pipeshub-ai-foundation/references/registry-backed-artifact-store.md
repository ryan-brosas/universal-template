<!-- capsule-v2 -->
# Registry-backed artifact store — how does a generic store(content)->id protocol survive registry outages without losing same-request reads?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** tool results must persist durably AND read back fast within the request — what happens when the durable side fails?

## L1 in-memory + L2 registry with write-through and fail-open fallback
**Path/Symbol:** `backend/python/app/agents/agent_loop/artifact_store.py:34-134` (`RegistryBackedStore`, `build_artifact_store` :125); direct tests `backend/python/tests/unit/agents/adapter/test_artifact_store.py`.
**Signature:** `store(content, *, tool_name="", result_schema=None, session_id=None) -> str`; `get(artifact_id) -> str | None`; `get_schema/get_tool_name`.
**Data Shape:** L1 = InMemoryArtifactStore (`_data: {id:(now,content)}`, `_schemas`, `_tool_names`); L2 = ArtifactRegistryService.register(...) → VersionManager.create() → blob save + graph node upsert + permission edges.

### Decisive source
```python
try:
    metadata = await self._registry.register(...)
except Exception:
    logger.warning(
        "RegistryBackedStore.store: registry.register() failed for "
        "tool %r — falling back to in-memory only", ...)
    return await self._l1.store(content, tool_name=tool_name,
        result_schema=result_schema, session_id=session_id)
aid = metadata.artifact_id
self._l1._data[aid] = (self._l1._now(), content)
```

**Flow:** store → registry (durable source of truth; name `tool_result_<tool>.json`, type TOOL_RESULT, is_temporary=True) → seed L1 manually so same-request reads never hit blob → get → L1 first, else registry.get_content with decode+backfill into L1.
**Invariant:** on registry failure the write DEGRADES to in-memory-only (this request still works; durability is sacrificed loudly in logs) rather than failing the tool result. The manual L1 seeding after register is deliberate — going through the public L1 API would double-store. `build_artifact_store` returns plain InMemoryArtifactStore when no registry/conversation exists (tests/standalone).

### Direct test
**Probe:** `tests/unit/agents/adapter/test_artifact_store.py` — execute `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_artifact_store.py -q` (passed at pin). Deterministic anchor: `grep -c 'InMemoryArtifactStore' app/agents/agent_loop/artifact_store.py` → 7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "RegistryBackedStore InMemoryArtifactStore build_artifact_store registry fallback", limit: 4, fields: ["signature", "name", "file"] });
// resolves artifact_store.py Class/Methods line-exact
```

## Verdict
Adopt the two-tier adapter for protocol-over-rich-backend bridging: write-through both tiers, manual L1 seeding, fail-open degradation to memory-only, factory downgrade for standalone runs. Adapt registry interface and naming. Omit VersionManager/blob/graph edge internals (owned by the artifact-store durability capsules from pass 12).
