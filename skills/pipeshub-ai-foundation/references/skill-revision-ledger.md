<!-- capsule-v2 -->
# Skill revision ledger — how do append-only versions avoid id collisions while rollback stays monotonic?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** When every update overwrites one document, how do you snapshot history so two edits in the same millisecond can't destroy a revision — and why does rollback never reuse version numbers?

## Version-keyed snapshot ids + patch-bump-on-every-write + restore-as-new-revision
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/graph_store.py` — `_bump_patch` (:88-96), `_SEMVER_RE` (:85), `_snapshot_revision` (:511-539), `update_skill` (:368-390), `rollback` (:474-503), `list_versions` (:449-463), `get_version` (:465-472), `delete_skill` (:401-410).
**Signature:** `def _bump_patch(version: str) -> str` (storage-level, non-semver/missing → `"1.0.1"`, never raises); `async def _snapshot_revision(current_doc: dict, now: int) -> None`; `async def rollback(name: str, version: str) -> SkillMetadata`.
**Data Shape:** Version doc: `{id: f"{skill_key}_v{version}", orgId, skillKey, name, version, content, resourcePaths/resourceContents, summary, updatedBy, createdAtTimestamp}`. `SkillVersionInfo(version, updated_by, created_at, summary)` sorted newest-first by created_at string.

### Decisive source
```python
# Why the snapshot id is keyed on VERSION, not on the timestamp:
#     The doc `id` is keyed on `(skill_key, version)`, NOT `(skill_key,
#     now)`: `now` is an epoch-millisecond timestamp, and two snapshot
#     calls landing in the same millisecond ... would collide and silently
#     overwrite each other via batch_upsert_nodes's id-based upsert —
#     losing a whole revision. `version` is safe here specifically because
#     it's monotonically bumped and never reused.
version = current_doc.get("version") or "1.0.0"
version_doc = {"id": f"{skill_key}_v{version}", ..., "content": current_doc.get("content", ""), ...}

# And in update_skill — archive FIRST, then bump the incoming content:
await self._snapshot_revision(existing_doc, now)
bumped = skill.metadata.model_copy(update={"version": _bump_patch(existing_doc.get("version"))})
```

**Flow (update):** load existing → parse+validate new content → snapshot CURRENT doc into versions → bump incoming metadata's patch (existing version is authoritative, caller's version string ignored) → full-doc overwrite with usage carried forward → re-sync relation edges. **(rollback):** snapshot current TOO (rollback is itself an edit) → parse ARCHIVED content → bump it to a NEW patch number on top of current — never reuse the archived number → write as the new head. **(delete):** hard-delete node+edges but leave `agentSkillVersions` rows in place — audit value outlives the skill (they reference by `skillKey`, not live edges).
**Invariant:** (1) Snapshot-before-overwrite ordering is what makes history complete; the archived copy is the PRE-edit state including its old version number. (2) Version numbers are monotonic and never reused — this is exactly what makes them valid unique ids for snapshots. (3) A non-semver stored version resets to 1.0.1 instead of raising: version strings are storage internals, never user-validated input. (4) Timestamps are collision-prone keys at millisecond resolution (trivially reproducible in fast tests). (5) Rollback creates a new head so a second rollback can always distinguish restored-copy from original.
**Probe:** `backend/python/tests/unit/agents/adapter/test_skills_graph_store.py::TestRevisionRoundTrip` — `test_snapshot_ids_dont_collide_within_the_same_millisecond` (:159), `test_rollback_unknown_version_raises` (:187), `test_update_preserves_usage_counters` (:199), plus the create→update→list→get→rollback round trip (:127).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_snapshot_revision _bump_patch agentSkillVersions rollback version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt version-keyed snapshot ids, snapshot-then-bump update order, and restore-as-new-revision semantics verbatim — they solve the upsert-collision and history-monotonicity problems in any id-upserted KV/doc store, graph or not; adapt the semver regex and reset default to host conventions; omit delete-preserves-history only if your compliance regime says otherwise. Direct tests pin all three behaviors including the same-millisecond collision case.
