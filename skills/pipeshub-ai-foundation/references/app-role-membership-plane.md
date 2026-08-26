<!-- capsule-v2 -->
# App-role membership plane — how do vendor roles (role→user rosters) become ROLES nodes with user edges, and what happens when a role is deleted at the source?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Roles are the third permission principal beside users and groups — how are they created, re-synced, and torn down, and which deletion asymmetry must a porter reproduce exactly?

## Role upsert mirrors groups; deletion is lookup-gated with False-on-missing
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `on_new_app_roles` (:1939–2019), `on_app_role_deleted` (:2529–2578).
**Signature:** `async def on_new_app_roles(self, roles: list[tuple[AppRole, list[AppUser]]]) -> None` / `async def on_app_role_deleted(self, external_role_id: str, connector_id: str) -> bool`, both `@retry_on_deadlock()`.
**Data Shape:** AppRole carries `id`, `connector_id`, `source_role_id` (vendor role id), `name`, `org_id`. Deletion returns `bool` and is the ONLY member of the delete family that answers False for "not found" — group deletion answers True.

### Decisive source
```python
existing_app_role = await tx_store.get_app_role_by_external_id(
    connector_id=role.connector_id, external_id=role.source_role_id)
if existing_app_role is None:
    ...                                   # keep fresh uuid
else:
    role.id = existing_app_role.id        # adopt stored identity
    role.updated_at = get_epoch_timestamp_in_ms()
    await tx_store.delete_edges_to(to_id=role.id,          # wholesale membership reset
        to_collection=CollectionNames.ROLES.value, collection=CollectionNames.PERMISSION.value)
await tx_store.batch_upsert_app_roles([role])
# member loop identical to groups: email→user or warn+continue; PermissionType.READ edges
```
```python
# on_app_role_deleted
app_role = await tx_store.get_app_role_by_external_id(connector_id=..., external_id=external_role_id)
if not app_role:
    self.logger.warning(f"Cannot delete role: Role with external ID {external_role_id} not found in database")
    return False
await tx_store.delete_nodes_and_edges([app_role.id], CollectionNames.ROLES.value)  # node + ALL edges
return True
```
**Flow:** same five-step choreography as user groups (resolve-by-external-pair → adopt-id → wipe inbound PERMISSION edges → upsert → rebuild member edges). Deletion: resolve by `(connector_id, external_role_id)`; missing ⇒ warn + **False**; found ⇒ `delete_nodes_and_edges` removes the ROLES node together with every PERMISSION/BELONGS_TO edge in one call ⇒ True.
**Invariant:** (1) role membership obeys the same rebuild-whole-roster contract as groups — partial rosters replace; (2) role DELETION is strict (False when absent, no node touched), while USER-group deletion (`on_user_group_deleted` :2242–2291) treats "already gone" as success (**True**): the asymmetry is deliberate — role-delete callers surface errors to admins, group-delete callers converge on desired state; (3) teardown always goes through `delete_nodes_and_edges`, never a bare node delete that would strand permission edges.
**Probe:** `grep -c 'delete_nodes_and_edges' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `4`; direct tests `tests/unit/connectors/core/test_data_source_entities_processor.py`: `test_creates_new_role_with_members` :894 plus the `on_app_role_deleted` describe block (~:2440+, not-found/ok cases green in battery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "on_new_app_roles get_app_role_by_external_id batch_upsert_app_roles", limit: 10 });
```

## Verdict
Adopt the mirror-choreography between group and role upserts and the strict-vs-lenient delete-return asymmetry; adapt edge collections and role doc fields; omit vendor-specific role semantics. Coverage caveat: none — coverage clean, tests executed green at pin.
