<!-- capsule-v2 -->
# Reindex double-click latch — where must the "reindex already running" 409 be checked, and why twice?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does `POST /knowledge/reindex_for_config` distinguish "please wait" from "reindex failed", and why is the in-flight guard evaluated both before AND after acquiring the lock?

## Pre-lock guard for UX + post-lock re-check for correctness, same structured 409
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_routes.py:763-835` (`reindex_for_config_change`); helper plane `knowledge_reindex.py::migrate_and_reindex_for_agent`.
**Signature:** `async def reindex_for_config_change(request, agent_id: Optional[str] = None)` → `{triggered, target, collections}` (same shape the old auto-trigger returned so FE arming code works unchanged); conflicts → HTTP 409 `{error: "reindex_in_progress", collections, message}`.
**Data Shape:** in-flight match predicate: collection == `kb_agent_{sanitized}` OR startswith `kb_agent_{sanitized}_` — the prefix+underscore form matches per-config-hash sub-collections, not other agents whose ids merely share a prefix.

### Decisive source
```python
# knowledge_routes.py:781-785 (pre-lock) and :808-825 (post-lock)
# Reject if a reindex is already in flight for this agent. Without this,
# a rapid double-click on Re-index hits engine.reindex's own busy check
# and the migration helper maps it to a generic ``reindex_failed`` toast
# -- confusing for what is really a "please wait" condition. Same shape
# as patch_draft_knowledge's Layer 1 guard so the FE can reuse handling.
...
    async with agent_draft_lock(str(agent_id)):
        # Re-check now that we're serialized -- two Re-index clicks (or a
        # concurrent publish) can both pass the pre-lock guard above; only
        # the first to acquire the lock should start a reindex.
```
The lock serializes against concurrent PATCH/publish because all of them mutate `engine._config`; the reindex must not interleave with a publish's commit. The deferred pointer-flip spawned inside is fire-and-forget and takes the lock later.

**Flow:** engine missing → 503 → sanitize agent id → pre-lock in-flight scan → 409 with sorted collections → acquire `agent_draft_lock` → RE-scan (TOCTOU closure) → `migrate_and_reindex_for_agent` under the lock → return result → any failure: generic 500 body, full detail log-only.
**Invariant:** A busy-condition conflict must surface as a distinct machine-readable 409 ("wait"), never collapse into a failure toast ("retry"); and a check-then-act guard that matters is ALWAYS re-evaluated after acquiring the serializing lock, because two requests can both observe "not running" before either acquires.

**Probe:** `tests/unit/test_knowledge_reindex_in_progress_guard.py` (publish/flip + in-progress guard behavior).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "reindex_for_config_change migrate_and_reindex_for_agent reindex_in_progress 409", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-checked latch pattern for any long-running admin action with its own busy state. Adapt the lock/collection naming. Omit the pre-lock branch only if your client tolerates generic failure mapping (it shouldn't). Direct tests cover the guard family.
