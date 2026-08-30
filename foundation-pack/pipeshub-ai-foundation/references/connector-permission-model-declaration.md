<!-- capsule-v2 -->
# Declared permission model — how does the query layer learn whether a connector's records need per-user ACL resolution WITHOUT importing connector code?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Where should "does this source have real per-record ACLs or is everything app-visible" be declared so permission resolution stays a data lookup?

## Denormalized declaration + safe-default backfill
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_builder.py:` `ConnectorConfigBuilder.with_permission_model` (:102-119); `registry/connector_registry.py:` `_permission_model_for` (:209-218), `sync_with_database` backfill loop, `_create_connector_instance` `'permissionModel': self._permission_model_for(metadata)` (:508-509).
**Signature:** `def with_permission_model(self, model: PermissionModel) -> '...'` raising `ValueError` on non-enum; `_permission_model_for(metadata) -> str` defaults to `PermissionModel.RECORD_LEVEL.value`.
**Data Shape:** `PermissionModel` ∈ {RECORD_LEVEL (default), APP_LEVEL}; stored BOTH inside decorator `config["permissionModel"]` AND denormalized onto every instance doc row.

### Decisive source
```python
def _permission_model_for(metadata):
    """RECORD_LEVEL is the safe default: it resolves visibility per user, so a
    connector that forgets to declare can only under-share."""
    config = metadata.get('config') or {}
    return config.get('permissionModel') or PermissionModel.RECORD_LEVEL.value

# builder docstring (the porting warning):
# Set APP_LEVEL only when the source has no per-record ACLs ... Leaving the
# RECORD_LEVEL default is always safe; declaring APP_LEVEL wrongly would WIDEN
# who can see the connector's records.
```

**Flow:** connector declares (or omits) model at build time → every NEW instance doc gets the resolved value stamped at creation ("Denormalized off the decorator so the query service can route permission resolution without importing connector code") → each startup, `sync_with_database` diffs stored vs currently-declared and updates drift (reclassifications included), tolerating failures.
**Invariant:** Default is RECORD_LEVEL (under-share beats over-share). The denormalized column exists precisely so hot query paths never import vendor adapter modules — preserve that decoupling or the query service gains a connector-code dependency. APP_LEVEL connectors write one blanket ORG/creator-USER permission per record instead of per-user edges.
**Probe:** `grep -c 'if not record.org_id:' app/connectors/core/base/data_processor/data_source_entities_processor.py` → `1` (org override seam pairs with this); `grep -c '_permission_model_for' app/connectors/core/registry/connector_registry.py` → `3`. Direct suite: `tests/unit/connectors/core/registry/test_permission_model.py` (15 tests).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "permissionModel APP_LEVEL RECORD_LEVEL connector", limit: 5 });
```
**Verdict:** Adopt declaration-at-registration + denormalize-to-row + backfill-on-drift; adapt enum values to host; omit PermissionModel constants tied to Arango imports (re-declare locally).
