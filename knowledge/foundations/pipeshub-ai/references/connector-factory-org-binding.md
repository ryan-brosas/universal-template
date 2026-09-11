<!-- capsule-v2 -->
# Factory org-binding + beta registry — why does the factory overwrite `data_entities_processor.org_id` after construction?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Multi-org deployments: where does a connector instance learn WHICH org its records belong to, given the processor was constructed earlier with a fallback?

## Post-construction override documented as the multi-org fix
**Path/Symbol:** `backend/python/app/connectors/core/factory/connector_factory.py:` `_connector_registry` slugged-key map (:88-139), `create_connector` (:196-243), `_run_sync_and_invalidate` (:292-305), `initialize_beta_connector_registry`/`list_beta_connectors` (:152-172); `base/token_service/startup_service.py` wires refresh services at boot.
**Signature:** `async def create_connector(cls, name, logger, data_store_provider, config_service, connector_id, scope, created_by, org_id=None, **kwargs) -> BaseConnector | None`.
**Data Shape:** Registry keys are lowercase slugs WITHOUT spaces ("sharepointonline", "gmailworkspace", "driveworkspace") — distinct from display names ("SharePoint", "Gmail") used by the metadata registry; beta classes registered only when flag initialized.

### Decisive source
```python
if connector is not None:
    if org_id and getattr(connector, "data_entities_processor", None) is not None:
        # The processor's initialize() resolves an arbitrary orgs[0] fallback; connectors read
        # self.data_entities_processor.org_id live at sync time, so overriding it here makes
        # every record/edge use the connector's actual org (multi-org fix).
        connector.data_entities_processor.org_id = org_id
```
Sync path also closes the loop:
```python
finally:
    await notify_connector_sync_completed(connector_id, org_id)   # drop accessible-record cache like EventService does
```

**Flow:** slug lookup → class-level `create_connector` builds instance → factory stamps live org_id onto shared processor (connectors read it AT SYNC TIME, not construction) → optional notification service injection → `create_and_start_sync`: init() → read selectedStrategy from config → MANUAL skips sync entirely; otherwise task-manager `start_sync` wrapping `_run_sync_and_invalidate` which ALWAYS invalidates the org's accessible-records cache even when run_sync raises (finally-block).
**Invariant:** Two registries exist ON PURPOSE: display-name metadata registry (UI/catalog) vs slug-keyed class registry (dispatch). The org stamp must happen post-construction because processors are shared/cached while instances are per-tenant. Cache invalidation on manual syncs is mandatory-parity with the event-service path or permission cache goes stale.
**Probe:** `grep -c 'data_entities_processor.org_id = org_id' app/connectors/core/factory/connector_factory.py` → `1`; suite `tests/unit/connectors/test_connector_factory.py` (31 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "ConnectorFactory create_connector org_id multi-org", limit: 3 });
```
**Verdict:** Adopt dual-registry split + post-construction org binding + finally-invalidate sync wrapper; adapt slug rules.
