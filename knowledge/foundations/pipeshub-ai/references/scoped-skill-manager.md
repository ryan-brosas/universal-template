<!-- capsule-v2 -->
# Scoped skill manager — how do you give one agent a narrowed read view of the shared skill catalog without touching the library?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you restrict WHICH skills a specific agent can see and load this turn (assignment axis) — orthogonal to user/visibility scoping — while writes, versions, health, and usage pass through untouched?

## Read-path-only wrapper: filter the 5 reads, gate the 2 loads, delegate everything else
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/scoped_manager.py` — `ScopedSkillManager` (:40-94); construction policy in `manager_factory.py::build_runtime_skill_manager` + `skills_wiring.build_skill_manager`.
**Signature:** `__init__(manager: SkillManager, allowed_names: set[str])`; overrides `catalog_snapshot()`, `list_skills(filter)`, `search(query, *, category, subcategory, tags, status, source, limit)`; `activate_skill(name, session_id)` / `load_resource(name, path)` raise `RegistryError` when invisible; everything else flows through `__getattr__` delegation.
**Data Shape:** `allowed_names` comes from the agent's data-declared `context.agent_skills` assignment. EMPTY set = NO explicit assignment = full unfiltered catalog (today's behavior unchanged) — so the factory only constructs this wrapper at all when the assignment is non-empty. Wrapping only ever NARROWS; it never widens or reorders upstream semantics.

### Decisive source
```python
async def search(self, query="", *, category=None, ..., limit=10):
    # Over-fetch, then filter — the underlying index doesn't know about
    # per-agent scoping, so a naive `limit` passthrough could return
    # fewer than `limit` visible matches even when more exist.
    matches = await self._manager.search(..., limit=max(limit * 4, limit))
    return [m for m in matches if self._visible(m.skill.name)][:limit]

async def activate_skill(self, name, session_id=None):
    if not self._visible(name):
        raise RegistryError(f"Skill {name!r} is not assigned to this agent")
    return await self._manager.activate_skill(name, session_id)
```

**Flow:** the prompt builder's tier-1 reads (`catalog_snapshot`/`list_skills`/`search`) get post-filtered lists → tier-2/3 loads (`activate_skill`/`load_resource`) check visibility FIRST and raise without calling the manager → every other method (`create/update/delete`, versions, health, usage tracking) resolves via `__getattr__` straight to the inner manager, because write authority is a governance question the agent already had; assignment scoping is only "what can this agent see/load". The Open/Closed win: `agent_loop_lib` is untouched — pure adapter-layer decorator.
**Invariant:** (1) Filter AFTER over-fetching with `max(limit*4, limit)` then truncate to `limit` — passing `limit` through naively silently under-fills visible results. (2) Disallowed loads must raise WITHOUT reaching the inner manager (no accidental activation). (3) Empty allowlist means unscoped, not zero skills. (4) The wrapper wraps ONLY the read/activation surface the prompt builder and the five skill tools actually walk.
**Probe:** `backend/python/tests/unit/agents/adapter/test_scoped_skill_manager.py` — `test_overfetches_and_filters_to_limit` (:54), `test_disallowed_skill_raises_without_calling_manager` (:98/:118), `test_empty_allowlist_hides_everything` (:32 — note: constructing with empty IS hiding in the class contract; the factory simply never does), `test_unscoped_methods_pass_through_via_getattr` (:129).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ScopedSkillManager allowed_names catalog_snapshot activate_skill", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the read-surface-only decorator with over-fetch-then-filter search, deny-before-inner-call loads, and `__getattr__` passthrough for governance methods; adapt the ×4 over-fetch factor and error type to host; omit the two-profile factory split if the host has no management API sharing the same manager stack. Direct-test coverage is strong.
