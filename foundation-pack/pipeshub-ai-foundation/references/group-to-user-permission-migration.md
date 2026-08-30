<!-- capsule-v2 -->
# Group→user permission migration — how do you dissolve a group while preserving every member's effective access, with upgrade-only conflict resolution?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When a source system deletes a group (or a "pseudo-group" per user), how are its outbound permission edges transferred to a concrete user WITHOUT granting anything new and WITHOUT losing the strongest existing right?

## Copy-or-upgrade migration over PERMISSION_HIERARCHY, batch-committed
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `migrate_group_permissions_to_user` (:2310–2474), constants :55–64.
**Signature:** `async def migrate_group_permissions_to_user(self, group_id: str, user_email: str, connector_id: str, tx_store: TransactionStore | None = None) -> None` — optional tx_store makes it join the CALLER's transaction (recursive self-call creates one when None).
**Data Shape:** Group's edges fetched via `tx_store.get_edges_from_node(from_node_id=f"groups/{group_id}", edge_collection="PERMISSION")`; each raw Arango edge = `{_key, _to: "<collection>/<id>", role}`. Hierarchy module constant: `PERMISSION_HIERARCHY = {"READER": 1, "COMMENTER": 2, "WRITER": 3, "OWNER": 4}`; unknown roles score 0 via `.get(role, 0)`.

### Decisive source
```python
target_parts = target_node_id.split("/", 1)
if len(target_parts) != ARANGO_NODE_ID_PARTS:   # ==2 — "collection/id"
    continue                                    # malformed _to silently skipped
role_str = edge.get("role", "READER")
try:
    permission_type = PermissionType(role_str)
except ValueError:
    permission_type = PermissionType.READ       # invalid vendor role degrades to READ
...
existing_role_level = PERMISSION_HIERARCHY.get(existing_role, 0)
new_role_level = PERMISSION_HIERARCHY.get(permission_type.value, 0)
if new_role_level > existing_role_level:        # STRICTLY greater — equal never rewrites
    await tx_store.delete_edge(...)             # delete-then-recreate to change the role
    ...new_permission_edges.append(upgraded_edge)
else:
    skipped_count += 1                          # same or weaker: keep the user's own edge
```
**Flow:** no tx ⇒ open one and recurse → resolve user by email (missing ⇒ warn + return, nothing written) → fetch all PERMISSION edges FROM the group node → per edge: split `_to`, coerce role with READ fallback → duplicate-check user→target edge: absent ⇒ queue copy; present-but-weaker ⇒ delete + queue upgrade; equal/stronger ⇒ skip → ONE `batch_create_edges` for every copy+upgrade at the end → log migrated/skipped counts. Always returns None (counts live in logs only).
**Invariant:** (1) migration can only PRESERVE or UPGRADE — it never downgrades an existing direct permission (`>` not `>=`); (2) upgrades must delete the old edge first because the edge doc carries the role field — upserting blindly would leave two competing edges; (3) malformed `_to` and unresolvable users abort that EDGE only, never the whole migration (per-edge error containment); (4) all writes land in one final batch inside one transaction so partial migrations cannot commit.
**Probe:** `grep -cF 'PERMISSION_HIERARCHY.get' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `2` (:2398 existing, :2399 new); `grep -c 'ARANGO_NODE_ID_PARTS' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `2`; suite `tests/unit/connectors/core/test_data_source_entities_processor.py` migrate describe (~:1249+): `test_upgrades_existing_permission` :1366, `test_skips_existing_permission_same_or_higher` :1391, `test_invalid_role_string_uses_default` :1415 — green in executed battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "migrate_group_permissions_to_user PERMISSION_HIERARCHY", limit: 10 });
```

## Verdict
Adopt copy-or-upgrade semantics with the strict-> comparison, per-edge error containment, and single-batch commit for any permission-dissolution port; adapt the hierarchy ladder to your role vocabulary; omit Arango `_to` parsing in favor of your store's id format (but keep the two-part validation). Coverage caveat: none — coverage clean, tests green at pin.
