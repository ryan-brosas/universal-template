<!-- capsule-v2 -->
# Permission-edge resolution — how do four entity types become record permission edges, and why do unknown groups/roles get DROPPED?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Vendors emit permissions for users/groups/roles/org; local DB may not know every principal yet — what is the write policy per entity type?

## Resolve-or-drop per edge with ORG as the only synthetic source
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `_handle_record_permissions` (:766-846) — USER via email lookup, GROUP via `(connector_id, external_id)`, ROLE via external_id, ORG via `self.org_id`; edges always Entity→RECORDS collection via `permission.to_arango_permission(from_id, from_collection, record.id, RECORDS)`.
**Signature:** `async def _handle_record_permissions(record, permissions, tx_store) -> None`; batch-insert into PERMISSION collection when any resolved.
**Data Shape:** `Permission(entity_type, email|external_id, type)`; ANYONE/ANYONE_WITH_LINK/DOMAIN arms present but commented out (upstream TODO).

### Decisive source
```python
if user_group:
    from_id = user_group.id; from_collection = CollectionNames.GROUPS.value
else:
    self.logger.warning(f"User group with external ID {permission.external_id} not found in database")
    continue                      # DROP: no placeholder group is fabricated
...
if from_id and from_collection:
    record_permissions.append(permission.to_arango_permission(...))
# external users: warning + TODO — no PEOPLE row created either
```

**Flow:** per permission: resolve principal locally → unresolved ⇒ warn+continue (edge skipped, sync proceeds) → collect resolved edges → single batch insert. Whole body wrapped in try/except logging failures WITHOUT raising — permission-write errors never fail record ingestion (records remain, visibility may under-share until next sync).
**Invariant:** Under-share-by-default: unknown principals produce NO edge rather than a guess (a fabricated group id would grant or leak). ORG is the only entity resolvable without a lookup (uses processor org directly). Error containment: permission failures are logged, never propagated — record content must land even if ACLs lag.
**Probe:** `grep -c 'from_collection = CollectionNames.' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `14`; suites `test_data_source_entities_processor.py` (244 tests incl. permission paths) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_handle_record_permissions to_arango_permission EntityType", limit: 3 });
```
**Verdict:** Adopt resolve-or-drop + non-fatal containment; adapt principal lookups/collection names; note upstream TODO if porting external-user support (decide explicitly rather than inheriting the gap).
