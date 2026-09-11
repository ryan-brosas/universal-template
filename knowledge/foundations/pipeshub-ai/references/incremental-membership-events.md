<!-- capsule-v2 -->
# Incremental membership events — how are single member add/remove changes applied between full roster rebuilds, and what does a False return mean?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Webhook-style deltas (one user added/removed from one group) must not trigger the whole-roster rebuild — how does the single-edge add/remove path resolve principals, dedupe, and report outcomes to callers?

## Lookup-gated edge surgery with explicit tri-state outcome
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `on_user_group_member_removed` (:2105–2162), `on_user_group_member_added` (:2165–2239).
**Signature:** `async def on_user_group_member_removed(self, external_group_id: str, user_email: str, connector_id: str) -> bool` / `async def on_user_group_member_added(self, external_group_id: str, user_email: str, permission_type: PermissionType, connector_id: str) -> bool`, both `@retry_on_deadlock()`.
**Data Shape:** Both take the VENDOR group id + user email; resolution is email→USERS node and `(connector_id, external_id)`→GROUPS node. Added edges carry the CALLER's `permission_type` (unlike the READ-fixed bulk rebuild); removed edges are deleted by exact 4-tuple identity.

### Decisive source
```python
# removed: no existence pre-check — delete_edge IS the check
edge_deleted = await tx_store.delete_edge(
    from_id=user.id, from_collection=CollectionNames.USERS.value,
    to_id=user_group.id, to_collection=CollectionNames.GROUPS.value,
    collection=CollectionNames.PERMISSION.value)
if not edge_deleted:
    self.logger.warning(f"No permission edge found between user {user_email} and group {user_group.name} ...")
    return False
```
```python
# added: explicit duplicate gate BEFORE creating
existing_edge = await tx_store.get_edge(from_id=user.id, ..., to_collection=CollectionNames.GROUPS.value,
                                        collection=CollectionNames.PERMISSION.value)
if existing_edge:
    self.logger.debug(f"Permission edge already exists between {user_email} and group {user_group.name}")
    return False                                # duplicate is a False, NOT an exception
permission = Permission(external_id=user.id, email=user_email,
                        type=permission_type, entity_type=EntityType.GROUP)
await tx_store.batch_create_edges([permission.to_arango_permission(...)], collection=...)
return True
```
**Flow (both):** transaction → resolve user by email; missing ⇒ warn + False → resolve group by external pair; missing ⇒ warn + False → then remove deletes by exact tuple (absent edge = False) / add checks `get_edge` first (duplicate = False) before creating and returning True.
**Invariant:** (1) every failure mode returns False — unresolvable principal, absent group, nothing-to-do — exceptions are reserved for infra failures (which the deadlock retry may re-run); (2) add is check-then-create, so double-delivered webhooks converge instead of stacking edges; (3) remove needs NO pre-check: delete_edge's own hit/miss is the probe; (4) principal resolution failure NEVER fabricates an edge with a guessed id — under-share beats wrong-share.
**Probe:** `grep -c 'get_edge(' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `3` (add-duplicate :2196, migration dup-check :2387, plus one helper use); suite tests at :1013–:1186 (`on_user_group_member_removed` ×5 cases, `on_user_group_member_added` ×5 cases incl. unknown-user/group/dup) — green in executed battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "on_user_group_member_removed on_user_group_member_added get_edge", limit: 10 });
```

## Verdict
Adopt the False-means-nothing-done contract and check-before-create for incremental membership deltas; adapt the permission parameter to your role enum; omit Arango edge tuples for your store's identity. Coverage caveat: none — coverage clean, ten event-path tests green in battery.
