<!-- capsule-v2 -->
# Full-overwrite usage carry-forward — how do accumulated counters survive a whole-document CRUD style?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** If every create/update is a full-document upsert overwrite, what stops one edit from silently wiping the skill's usage history — and how do resources/maps survive backends that ban nested maps?

## Extract-before-overwrite + parallel-array encoding as the portable map representation
**Path/Symbol:** `backend/python/app/agents/agent_loop/skills/graph_store.py` — `_USAGE_FIELDS` (:104-107), `_default_usage` (:110-118), `_extract_usage` (:121-129), `_skill_to_doc` (:237-286, docstring :248-258), `_resources_to_fields` (:132-142), `_resources_from_doc` (:145-154), `write_resource`/`remove_resource` (:412-434).
**Signature:** `def _extract_usage(doc: dict) -> dict[str, Any]`; `def _skill_to_doc(skill, *, resources: dict[str,str], created_by, created_at, updated_at, updated_by=None, usage=None) -> dict`; `def _resources_to_fields(resources: dict[str,str]) -> dict[str,list[str]]`.
**Data Shape:** Usage counters: `usageTotalActivations`, `usageSuccessfulOutcomes`, `usageFailedOutcomes`, `usageLastActivated`, `usageFailureModes[]`, `usageImprovementNotes[]`. Resources stored as sorted index-aligned arrays `resourcePaths[]`+`resourceContents[]`; read falls back to legacy nested `resources` map.

### Decisive source
```python
# _skill_to_doc — the single place Skill→doc happens; content ALWAYS
# re-rendered here so denormalized fields and SKILL.md can never drift:
        "content": render_skill_md(skill),
        ...
    # every CRUD path does a full-document batch_upsert_nodes overwrite,
    # so a caller updating an EXISTING skill must pass
    # _extract_usage(existing_doc) through, or that skill's accumulated
    # usage history is silently wiped on every edit.
        doc.update(usage if usage is not None else _default_usage())

# _resources_to_fields — the Neo4j constraint in one comment:
#     Neo4j node properties can only be primitives or arrays thereof, so a
#     nested map on the doc works on Arango but throws
#     Neo.ClientError.Statement.TypeError on Neo4j — parallel arrays are
#     the primitive representation both backends accept natively.
```

**Flow:** update/rollback path: `_extract_usage(existing_doc)` → `_skill_to_doc(..., usage=...)` → full-doc `batch_upsert_nodes` → counters persist across the overwrite. Resource writes do NOT rewrite the whole doc — they read-modify-write ONLY the two array fields via `update_node` (+ timestamp). Reads reassemble `{path: content}` via `dict(zip(paths, contents))`, or fall back to the legacy nested map for pre-migration Arango docs.
**Invariant:** (1) The caller MUST thread `_extract_usage(existing_doc)` through every existing-skill overwrite — forgetting it doesn't error, it silently zeroes history (update_skill :386 and rollback :499 both comply). (2) `content` is always re-rendered from the domain model inside `_skill_to_doc`, never taken from caller input — denormalized frontmatter fields and body text are consistent by construction. (3) Maps become sorted parallel arrays (index alignment IS the join key); any new map-shaped field needs its own pair. (4) Partial updates (`update_node`) for resource-only edits avoid the extract problem entirely where a full overwrite isn't needed.
**Probe:** `backend/python/tests/unit/agents/adapter/test_skills_graph_store.py` — `TestRevisionRoundTrip.test_update_preserves_usage_counters` (:199), `TestNeo4jSafeEncoding.test_resources_survive_update_and_rollback` (:244), `test_legacy_nested_resources_map_still_readable` (:258), `test_audit_governor_appends_parallel_arrays` (:278).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "_extract_usage _resources_to_fields render_skill_md batch_upsert_nodes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt extract-before-full-overwrite for any accumulated state and parallel-array map encoding for primitive-only stores; adapt counter field names and whether resource edits go partial vs full to your store's semantics; omit the legacy nested-map fallback once no pre-migration docs remain. Direct tests cover all four behaviors named above.
