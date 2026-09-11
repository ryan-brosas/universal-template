<!-- capsule-v2 -->
# Instance creation contract — why is authType frozen at creation, and what makes a name collision safe across tenants?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When creating a connector instance row, which fields are immutable-by-design and what happens when the uniqueness check errors?

## Create-once identity with fail-open uniqueness
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_registry.py:` `_create_connector_instance` (:341-547), `_check_name_uniqueness` (:318-337), `update_connector_instance` (:1419-1522).
**Signature:** `async def _create_connector_instance(connector_type, instance_name, metadata, scope, created_by, org_id, *, selected_auth_type=None) -> dict | None` (raises ValueError on dup name); `async def _check_name_uniqueness(...) -> bool`.
**Data Shape:** Instance doc `{_key: uuid4, name, type, appGroup, authType, scope, orgId, permissionModel, isActive: False, isAgentActive: False, isConfigured: True, isAuthenticated: False, createdBy/updatedBy, timestamps}` + one `ORG_APP_RELATION` edge org→app created right after the node upsert.

### Decisive source
```python
# selected_auth_type is the auth type chosen by the user and stored in the database
# This cannot be changed after creation
if not selected_auth_type:
    raise ValueError(f"selected_auth_type is required when creating connector '{connector_type}'. ...")
if supported_auth_types and selected_auth_type not in supported_auth_types:
    raise ValueError(...)

except Exception as e:
    self.logger.error(f"Error checking name uniqueness: {e}")
    # On error, allow the operation (fail-open to avoid blocking)
    return True

except ValueError:
    raise          # duplicate-name ValueError re-raised as-is through create/update
except Exception:
    return None    # every other failure returns None, logged
```

**Flow:** verify org exists → uniqueness probe against graph provider (scope-aware: per-user for personal, per-org+user for team) → stamp immutable identity fields → `batch_upsert_nodes` then `batch_create_edges(ORG_APP_RELATION)` (edge failure ⇒ exception ⇒ None, no orphan node without tenant link... node exists but method reports failure) → telemetry `record_event("connector_added", {orgId, userId, email, domain, ...})`. Updates re-check uniqueness only when `name` changes and merge `{**existing, **updates}` stripping key/id fields before `update_node`.
**Invariant:** `authType` is write-once at creation (schema drift protection — stored credentials always match the chosen flow). Duplicate-name detection FAILS OPEN on infra error (a transient graph outage must not brick configuration), while genuine duplicates raise typed ValueError that survives both create and update paths unswallowed.
**Probe:** `grep -c 'selected_auth_type is required when creating' app/connectors/core/registry/connector_registry.py` → `1`; `grep -c 'fail-open to avoid blocking' app/connectors/core/registry/connector_registry.py` → `1`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_create_connector_instance selected_auth_type ORG_APP_RELATION", limit: 3 });
```
**Verdict:** Adopt write-once authType + fail-open uniqueness + edge-after-node creation order with explicit failure; adapt id/uuid and telemetry conventions.
