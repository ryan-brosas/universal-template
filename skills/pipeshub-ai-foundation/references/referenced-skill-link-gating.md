<!-- capsule-v2 -->
# Referenced-attachment link gating — how do agents attach skills they don't own without creating nodes or leaking a co-worker's skill?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When attaching a resource OWNED by another subsystem (skills), how do you link-only, re-validate at write time, and skip stale references without failing the whole request?

## Parse never creates; edge-time existence+ownership gate; skip-don't-fail
**Path/Symbol:** `backend/python/app/api/routes/agent.py:_parse_skills` (:1265–1288) and `_create_skill_edges` (:1291–1341).
**Signature:** `_parse_skills(raw: list[Any]) -> list[str]` (accepts `[{name}]` or `[name]`, dedupes order-preserving); `_create_skill_edges(agent_key, skill_names, org_id, user_key, graph_provider, logger, transaction=None) -> list[str]` (returns actually-linked names).
**Data Shape:** Skill doc key = `f"{org_id}_{name}"`; edge = `{_from: agentInstances/<agent>, _to: agentSkills/<org>_<name>, skillName: name, createdAt/updatedAtTimestamp}`; the response echoes only `linked_skills`.

### Decisive source
```python
for name in skill_names:
    skill_key = f"{org_id}_{name}"
    skill_doc = await graph_provider.get_document(skill_key, skills_collection, transaction=transaction)
    if not skill_doc or skill_doc.get("orgId") != org_id:
        logger.warning(f"Skipping unknown skill '{name}' for agent {agent_key}")
        continue
    if skill_doc.get("source") != "builtin" and skill_doc.get("createdBy") != user_key:
        logger.warning(f"Skipping skill '{name}' not owned by user {user_key} for agent {agent_key}")
        continue
    edges.append({...}); linked_names.append(name)
if edges:
    await graph_provider.batch_create_edges(edges, CollectionNames.AGENT_HAS_SKILL.value,
                                            transaction=transaction)
return linked_names
```

**Flow:** parse → per-name: resolve `{org}_{name}` doc inside the caller's transaction → org check (construction-bound tenancy) → ownership check (creator OR builtin-source) → collect edge → one batch insert of all passing edges → return linked names. Update-side replacement (:2879–2913) deletes ALL this agent's `agentHasSkill` edges then re-links in the SAME transaction — but only edges, never skill nodes.
**Invariant:** (1) Agent create/update NEVER creates a skill node — skills belong to the Skills management API; agents only reference. (2) The parse step is pure (no I/O); existence/ownership is re-validated at write time regardless of client claims ("Defense in depth (mirrors `GraphSkillStore._is_visible`)"). (3) A stale/unowned name is logged-and-skipped — it must never block agent creation. (4) The response reports what was ACTUALLY linked, not what was requested.
**Probe:** `tests/unit/agents/adapter/test_skills_graph_store.py` pins the tenancy/ownership predicates on the store side (org isolation :330–345, creator-scoping class :406+); route helper itself is unit-untested — coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_create_skill_edges agentHasSkill", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt link-don't-copy for cross-subsystem references plus write-time re-validation with skip-not-fail semantics and truthful linked-name responses. Adapt the ownership predicate (creator-or-builtin) to your authz model. Omit the PipesHub collection naming.
