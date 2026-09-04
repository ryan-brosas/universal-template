<!-- capsule-v2 -->
# Graph usage tracker — how does per-skill usage memory survive restarts without an atomic increment?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When the durable store has no `$inc`, how do you persist activation/outcome counters on the skill document itself, and which lost updates are acceptable?

## Read-modify-write counters onto the SAME doc the skill store owns
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/graph_tracker.py:GraphUsageTracker` (:58–130); field names defined by `app/schema/arango/documents.py::agent_skills_schema`.
**Signature:** `GraphUsageTracker(graph_provider, org_id, user_id)`; `record_activation(skill_name, session_id)`; `record_outcome(skill_name, session_id, success, notes="")`; `get_experience(skill_name) -> SkillExperience`; `get_underperforming(threshold=0.5)`; `get_unused(since_days=30)`. Implements `agent_loop_lib`'s `SkillUsageTracker` ABC (the in-memory tracker's durable twin).
**Data Shape:** Fields on `agentSkills`: `usageTotalActivations:int`, `usageSuccessfulOutcomes:int`, `usageFailedOutcomes:int`, `usageLastActivated:str(iso)`, `usageFailureModes:list[str]` (capped `_MAX_NOTES = 20`), `usageImprovementNotes:list[str]`; key = `{org_id}_{name}`.

### Decisive source
```python
async def record_outcome(self, skill_name, session_id, success, notes=""):
    doc = await self._get_org_doc(skill_name)
    if doc is None:
        logger.debug("GraphUsageTracker: skipping outcome for unknown skill %r", skill_name)
        return
    updates = {"updatedAtTimestamp": get_epoch_timestamp_in_ms()}
    if success:
        updates["usageSuccessfulOutcomes"] = int(doc.get("usageSuccessfulOutcomes") or 0) + 1
    else:
        updates["usageFailedOutcomes"] = int(doc.get("usageFailedOutcomes") or 0) + 1
        if notes:
            failure_modes = list(doc.get("usageFailureModes") or [])
            failure_modes.append(notes)
            updates["usageFailureModes"] = failure_modes[-_MAX_NOTES:]
    await self._graph.update_node(self._key(skill_name), _SKILLS, updates)

# org guard on EVERY read — the key embeds the org but the check is explicit
doc = await self._graph.get_document(self._key(name), _SKILLS)
if doc is None or doc.get("orgId") != self._org_id:
    return None
```

**Flow:** resolve org doc → unknown skill ⇒ debug-log + no-op (tracking must never break a run) → build a PARTIAL update dict (only touched counters + `updatedAtTimestamp`) → `update_node`. Reads project the raw fields into a neutral `SkillExperience`; health queries (`get_underperforming`) require `total > 0` so never-used skills don't flunk; `get_unused` skips unparseable timestamps rather than guessing.
**Invariant:** (1) Counters are read-modify-write, NOT atomic increments — rare lost updates under same-skill concurrency are EXPLICITLY accepted because this is a directional "heavily used / rarely fails" signal for `SkillManager.evaluate_skill_health`, not an exact audit count. (2) Unknown-skill writes are silent no-ops. (3) Failure notes are a bounded taste of WHY (`_MAX_NOTES=20`), not an audit log — that's `agentSkillVersions`. (4) Every read re-checks `orgId` even though the key already encodes it.
**Probe:** `tests/unit/agents/adapter/test_skills_graph_store.py::test_update_preserves_usage_counters` (:202–218 — two activations + one success survive `update_skill`'s full-document overwrite) and the cross-org isolation test (:330–345); direct tests exist, run them before porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "GraphUsageTracker record_activation usageTotalActivations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt durable usage as namespaced fields on the entity's own document with partial updates and bounded note lists; adopt the explicit lost-update tolerance rationale. Adapt the ABC shape (`SkillExperience`) and field prefixes to your schema. Omit the ArangoDB collection constants.
