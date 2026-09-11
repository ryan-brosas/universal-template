<!-- capsule-v2 -->
|# Best-effort invalidation hooks — how do sync/indexing write paths drop permission-cache entries without importing or failing?

## Module-global holder + notify functions that are no-ops unregistered and CANNOT raise; connector apps resolve their org via the ORG_APP_RELATION EDGE, not the orgId property
**Path/Symbol:** `backend/python/app/services/cache/invalidation_hooks.py` (whole file L1–103: `_state` dict-holder :39–40, init/get/reset :43–59, notify trio :62–102) + `accessible_records_cache.py::AccessibleRecordsInvalidator` :299–431 (`on_connector_sync_completed` :317–338, `on_kb_records_changed` :340–361 KB-type-gated, `on_record_indexed` :363–395 deliberately KB-only, `_org_for_app` :402–431 edge walk).
**Signature:** `async notify_connector_sync_completed(connector_id, org_id=None)`; `notify_kb_records_changed(kb_id, org_id=None)`; `notify_record_indexed(connector_name=None, connector_id=None, external_record_group_id=None, org_id=None)`.
**Data Shape:** hook sites call module functions — services register ONE invalidator at startup rather than threading it through ~50 constructor sites (DataSourceEntitiesProcessor count cited in docstring). Every wrapper try/excepts around an invalidator that ALREADY swallows.

### Decisive source
```python
# Connector apps do not carry `orgId` as a property -- only KB apps do --
# so the ORG_APP_RELATION edge is the answer for every connector, not a
# rare fallback. Reading only the property meant every connector-scoped
# invalidation resolved to None and silently did nothing.
edges = await self.graph_provider.get_edges_to_node(
    f"{CollectionNames.APPS.value}/{app_id}",
    CollectionNames.ORG_APP_RELATION.value)
for edge in edges or []:
    if not isinstance(edge, dict):
        continue                      # malformed entry costs only itself
    raw = str(edge.get("from_id") or edge.get("_from") or "")
    if raw:
        return raw.rsplit("/", 1)[-1] # neo4j bare id vs arango "organizations/<key>"
```

**Flow:** sync completion ⇒ invalidate BOTH connector key shapes (app-level string + per-user hash) for the resolved org. Record indexed ⇒ KB-only (connector records flip COMPLETED thousands-per-burst during a sync; per-record drops would keep the cache empty exactly when the graph is busiest — connectors invalidate ONCE on sync completion). Unresolved org logs a WARNING and skips (silent skip previously hid total invalidation failure).
**Invariant:** invalidation is best-effort end-to-end — TTL bounds whatever is missed; a no-op-unregistered global means tests and non-cache deployments need zero wiring. Backend idiom differences (neo4j `from_id` vs arango `_from` handle) normalise via rsplit("/") before comparison.
**Probe:** `backend/python/tests/unit/services/graph_db/test_accessible_records_provider_routing.py` (396L suite over the routing/merge surface these hooks protect); deterministic pins for THIS file: `grep -c 'if invalidator is None:' backend/python/app/services/cache/invalidation_hooks.py` == 3; `grep -c 'ORG_APP_RELATION' backend/python/app/services/cache/accessible_records_cache.py` ≥ 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "invalidate_connector ORG_APP_RELATION on_record_indexed", limit: 10 });
```

## Verdict
Adopt the register-once/no-op-unregistered hook façade, the dual-shape connector invalidation, KB-only record-indexed gating, and edge-based org resolution; adapt graph-provider calls to your store; omit the Arango/Neo4j duality if single-backend. Coverage caveat: hook module pinned by deterministic greps; the protected routing/merge surface ships its own upstream suite.
