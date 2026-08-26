<!-- capsule-v2 -->
# Registry↔database sync — when code removes a connector, how do orphaned tenant instances die without losing data?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What exact state transition happens to connector instances whose connector TYPE no longer exists in code after a deploy, and why is creation deliberately NOT part of startup?

## Deactivate-only reconciliation with flag backfill
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_registry.py:` `ConnectorRegistry.sync_with_database` (:598-667), `register_connector` (:157-181), `discover_connectors` (:184-207).
**Signature:** `async def sync_with_database(self) -> bool`; scans `CollectionNames.APPS` documents against in-memory `self._connectors` populated by `register_connector` (metadata copies keyed by display name).
**Data Shape:** Instance doc carries `{_key, type, scope, orgId, isActive, isAgentActive, isConfigured, isAuthenticated, permissionModel, createdBy}`; deactivation writes ONLY `{isActive: False, isAgentActive: False}` via `batch_update_connector_status`.

### Decisive source
```python
for document in all_documents:
    connector_type = document.get('type')
    if connector_type == Connectors.KNOWLEDGE_BASE.value:
        continue                      # KB docs store "KB" but register as "Collections"
    doc_key = document.get('_key') or document.get('id')
    if connector_type not in self._connectors and is_active:
        keys_to_deactivate.append(doc_key)
    registered = self._connectors.get(connector_type)
    if registered and doc_key:
        expected = self._permission_model_for(registered)
        if document.get('permissionModel') != expected:
            stale_permission_models.append((doc_key, expected))
...
updated_count = await graph_provider.batch_update_connector_status(
    collection=self._collection_name, connector_keys=keys_to_deactivate,
    is_active=False, is_agent_active=False)
```

**Flow:** startup discovers decorated classes via `__import__` + `hasattr(_connector_metadata)` scan → `sync_with_database` lists ALL app docs → skips the KB special case → batches deactivation of active-but-unregistered types → separately diffs stored `permissionModel` vs freshly declared value and best-effort `update_node`s each mismatch ("Backfilled permissionModel on N instances") → returns True even when nothing changed.
**Invariant:** Sync DEACTIVATES, never deletes — records/edges stay intact for rollback or re-registration. Creation is never done at startup (instances exist only after explicit configuration). Failure inside the permissionModel backfill is logged-not-raised: it costs cache sharing, never correctness.
**Probe:** `grep -c 'stale_permission_models' app/connectors/core/registry/connector_registry.py` → `5`; `grep -c '_KB_REGISTRY_KEY = "Collections"' app/connectors/core/registry/connector_registry.py` → `1`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ConnectorRegistry sync_with_database deactivate", limit: 3 });
```
(rank #1 `sync_with_database` :598-667.)
**Caveat:** direct suite `tests/unit/connectors/core/test_connector_registry_extended.py` covers discovery/deactivation mocks (41 tests); no live-Arango integration test — behavior pinned by unit mocks + this read.
