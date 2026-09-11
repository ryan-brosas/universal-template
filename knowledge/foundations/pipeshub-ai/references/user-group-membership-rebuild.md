<!-- capsule-v2 -->
# User-group membership rebuild — how does a vendor group sync become user→group PERMISSION edges without ever orphaning or duplicating membership?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When a connector re-sends its groups with members (every sync), how does the processor converge membership edges — what identifies a group across syncs, and why must old edges be deleted wholesale instead of diffed?

## External-id identity + delete-all-then-recreate membership
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `on_new_user_groups` (:1855–1936).
**Signature:** `async def on_new_user_groups(self, user_groups: list[tuple[AppUserGroup, list[AppUser]]]) -> None`, decorated `@retry_on_deadlock()`.
**Data Shape:** Input is `(AppUserGroup, list[AppUser])` tuples; AppUserGroup carries `id` (fresh uuid default_factory), `connector_id` (the connector INSTANCE id), `source_user_group_id` (vendor group id), `name`, `org_id`; AppUser carries `id`, `email`, plus vendor member id. Edges are generic dicts from `Permission.to_arango_permission(from_id, from_collection, to_id, to_collection)` = `{from_id, from_collection, to_id, to_collection, role, type, createdAtTimestamp, updatedAtTimestamp}` (`app/models/permission.py:34–62`).

### Decisive source
```python
existing_user_group = await tx_store.get_user_group_by_external_id(
    connector_id=user_group.connector_id,
    external_id=user_group.source_user_group_id)
if existing_user_group is None:
    ...  # keep fresh uuid
else:
    # Overwrite the new UUID with the existing one
    user_group.id = existing_user_group.id
    user_group.updated_at = get_epoch_timestamp_in_ms()
    # To Delete the previously existing edges to user group and create new permissions
    await tx_store.delete_edges_to(
        to_id=user_group.id,
        to_collection=CollectionNames.GROUPS.value,
        collection=CollectionNames.PERMISSION.value)
await tx_store.batch_upsert_user_groups([user_group])
...
for member in members:
    user = await tx_store.get_user_by_email(member.email) if member.email else None
    if not user:
        self.logger.warning(f"Could not find user with email {member.email} for UserGroup permission.")
        continue                                   # drop-with-warning, never fabricate
    permission = Permission(external_id=member.id, email=member.email,
                            type=PermissionType.READ, entity_type=EntityType.USER)
```
**Flow:** empty list → warn+skip → one transaction for ALL groups → per group: resolve by `(connector_id, source_user_group_id)`; existing ⇒ adopt stored id + bump updated_at + delete EVERY PERMISSION edge pointing at the group; upsert doc → for each member resolve internal user BY EMAIL (missing ⇒ warn+skip that member only) → build READ-type USER→GROUPS edges → single `batch_create_edges` per group.
**Invariant:** (1) group identity is the EXTERNAL id pair, never the generated uuid — the fresh uuid must be overwritten with the stored one BEFORE any edge is written or membership forks into a duplicate group node; (2) membership is rebuilt wholesale (delete_edges_to then recreate): no incremental diff exists, so re-delivery is idempotent by construction but a partial member list REPLACES membership — callers must always send the full roster; (3) unresolvable members are dropped with a warning, never silently fabricated as ids.
**Probe:** `grep -c 'delete_edges_to' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `5` (:674 message-entity reset, :914 ticket-user reset, :1641 record-groups, :1888 user-groups, :1972 roles); direct suite `tests/unit/connectors/core/test_data_source_entities_processor.py` — `test_creates_new_user_group_with_members` :774, `test_updates_existing_user_group` :837 (both green in executed battery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "on_new_user_groups batch_upsert_user_groups delete_edges_to", limit: 10 });
```

## Verdict
Adopt external-id identity + wholesale membership rebuild + email-keyed drop-with-warning resolution for any group-sync port; adapt collection names and the Permission edge shape to your graph store; omit the Arango-specific batch APIs. Coverage caveat: none — file has no recorded coverage issue and the two named tests execute green at pin.
