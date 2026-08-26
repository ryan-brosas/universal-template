<!-- capsule-v2 -->
# Atomic migrate-and-dissolve — how does a connector retire a group and hand its access to one user in a single all-or-nothing step?

**Source:** PipesHub AI Apache-2.0 `main@c28d133602543bd737b9791db84b76c5dee84ff7`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Migration + group deletion are two writes — how does the code guarantee a caller never ends up with the group gone but its permissions NOT transferred (access loss), or transferred twice (privilege duplication)?

## One transaction wraps resolve → migrate → delete
**Path/Symbol:** `backend/python/app/connectors/core/base/data_processor/data_source_entities_processor.py:` `migrate_group_to_user_by_external_id` (:2477–2526); production consumer `backend/python/app/connectors/sources/atlassian/confluence_cloud/connector.py` (:847–852).
**Signature:** `async def migrate_group_to_user_by_external_id(self, group_external_id: str, user_email: str, connector_id: str) -> None`.
**Data Shape:** Takes the VENDOR group id (not internal id) so connectors need no knowledge of graph identity; internally resolves to the stored AppUserGroup, then delegates to `migrate_group_permissions_to_user(group.id, ..., tx_store=tx_store)` passing ITS OWN transaction.

### Decisive source
```python
async with self.data_store_provider.transaction() as tx_store:
    group = await tx_store.get_user_group_by_external_id(
        connector_id=connector_id, external_id=group_external_id)
    if not group:
        self.logger.debug(f"Group with external ID {group_external_id} not found for connector {connector_id}")
        return                                   # already dissolved: success-shaped no-op
    await self.migrate_group_permissions_to_user(
        group_id=group.id, user_email=user_email,
        connector_id=connector_id, tx_store=tx_store)   # SAME tx — this is the whole point
    await tx_store.delete_user_group_by_id(group.id)    # node+edges gone only after migration
```
**Flow:** open transaction → resolve by external pair → absent ⇒ log-and-return (idempotent under vendor re-delivery) → run copy-or-upgrade migration inside the SAME transaction → delete the group node and all remaining edges → commit. The Confluence connector drives this per user during member sync (`connector.py:847`): each "pseudo-group" keyed by source_user_id is dissolved into that user's direct permissions inside a try/except that logs-and-continues, so one bad user never stalls the batch.
**Invariant:** (1) migration and deletion share one transaction — there is NO interleaving where permissions vanish with the group; (2) the external-id miss is a silent success-shaped return, making the operation retry-safe against duplicate sync events; (3) deletion reuses `delete_user_group_by_id`, which itself opens no new transaction when handed none by an outer scope.
**Probe:** `grep -n 'migrate_group_to_user_by_external_id' app/connectors/sources/atlassian/confluence_cloud/connector.py | wc -l` → `1`; suite `tests/unit/connectors/core/test_data_source_entities_processor.py`: `test_migrates_and_deletes_group` :2086 ("Migrates permissions and deletes group", green in battery).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "migrate_group_to_user_by_external_id delete_user_group_by_id", limit: 10 });
```

## Verdict
Adopt single-transaction dissolve-with-handover and the idempotent missing-group return; adapt which principal receives access (here always one email-resolved user); omit Confluence's pseudo-group convention unless porting that connector. Coverage caveat: none — coverage clean, test green at pin.
