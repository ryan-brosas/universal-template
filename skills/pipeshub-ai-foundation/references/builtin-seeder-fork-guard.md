<!-- capsule-v2 -->
# Builtin seeder fork guard — how do you auto-upgrade seeded skills without ever clobbering an org's edits?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** When a new pack version ships, how does the per-org seeding pipeline know a builtin-sourced skill was edited by the org — and which identity must perform the writes for fork detection to work at all?

## Dedicated SEED_IDENTITY + updatedBy-based _is_unmodified gate
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/builtin_seeder.py` — `BuiltinSkillSeeder` (:46-129), `SEED_IDENTITY = "system:builtin-seeder"` (:43), `_is_unmodified` (:125-129), `sync` (:77-97); caller-side gating in `manager_factory.py::sync_builtin_skills`.
**Signature:** `__init__(packs_root: str, *, validator: SkillValidator | None = None)` (parses + validates ALL packs at construction; zero packs → loud RuntimeError at startup); `pack_versions -> dict[str, str]`; `async sync(store: GraphSkillStore) -> None`; `async _is_unmodified(store, name) -> bool`.
**Data Shape:** Each org gets its OWN `agentSkills` doc per builtin skill (`{org_id}_{name}` key) — never one shared global row. Writes go through `GraphSkillStore` constructed with `user_id=SEED_IDENTITY`, so every seeded write stamps `createdBy/updatedBy = "system:builtin-seeder"` using the same provenance fields all other writes already use. Pack identity rides `metadata.pack_version`.

### Decisive source
```python
async def _is_unmodified(self, store, name) -> bool:
    provenance = await store.get_provenance(name)
    if provenance is None:
        return True
    return provenance.get("updated_by") in (None, SEED_IDENTITY)
    # ^ "seeded, never touched" vs "a human or skill_writer edited this"
    #   decided from the SAME field every write already stamps

async def sync(self, store):
    existing = {m.name: m for m in await store.list_skills(SkillFilter(source=SkillSource.BUILTIN))}
    for skill in self._packs:
        current = existing.get(skill.metadata.name)
        if current is None:
            await self._create(store, skill)
        elif current.pack_version != skill.metadata.pack_version:
            await self._maybe_upgrade(store, skill, current.pack_version)  # fork-gated inside
        # else: already at the current pack version — nothing to do.
```

**Flow:** construction parses+validates once per process (zero packs or invalid frontmatter in OUR OWN packs fails loudly — lenient skip is only correct for third-party content) → callers pre-check `current == seeder.pack_versions` to skip the round-trip entirely → `sync` diffs disk packs against the org's BUILTIN-sourced catalog → create missing / upgrade version-drifted-but-unmodified / SKIP upgrade when `updated_by` belongs to anyone but the seeder (log it, leave the org's fork alone) → every write still passes the validator and lands a real revision snapshot. Idempotent by construction: upserts keyed `{org_id}_{name}`, so concurrent seed attempts converge without a lock.
**Invariant:** (1) The store used for seeding MUST be bound to `SEED_IDENTITY`, not the acting user — reusing the real-user store stamps `createdBy` as that user and makes seeded skills indistinguishable from human-authored ones, defeating fork detection for every later user in the org. (2) An org-edited copy is NEVER silently overwritten by a pack upgrade; edits by the seed identity itself still count as unmodified. (3) Seeding failures are logged-and-swallowed at the call site — builtin seeding is an enhancement, never a hard dependency for skills to work this turn. (4) Missing provenance reads as unmodified (fail-open toward upgrade).
**Probe:** `backend/python/tests/unit/agents/adapter/test_builtin_skill_seeder.py` — `test_org_edited_copy_is_not_overwritten_by_upgrade` (:136), `test_seed_identity_edits_are_still_auto_upgraded` (:156), `test_unmodified_copy_upgrades_to_new_pack_version` (:114), `test_zero_packs_raises_at_construction` (:192).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "BuiltinSkillSeeder SEED_IDENTITY _is_unmodified sync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dedicated system-identity writer + reuse of ordinary provenance fields as the fork detector (no extra state column), the loud-at-construction validation of first-party packs, and the swallow-failures enhancement posture; adapt pack-version source and log wording to host; omit npm-style remote resolution (the repo's own future Phase 4). Direct-test coverage is strong.
