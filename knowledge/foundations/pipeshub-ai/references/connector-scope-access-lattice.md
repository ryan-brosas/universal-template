<!-- capsule-v2 -->
# Scope access lattice — why can a non-admin teammate VIEW a team connector's stats but still not UPDATE it?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** A porter copying "team = admins manage" will silently break stats visibility or widen mutation rights — which predicate gates reads vs writes?

## Two predicates that intentionally disagree
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_registry.py:` `_can_access_connector` (:248-280, mutations), `can_user_view_connector` (:282-315, reads).
**Signature:** `async def _can_access_connector(instance, user_id, *, is_admin) -> bool`; `async def can_user_view_connector(connector_id, instance, user_id, *, is_admin) -> bool`.
**Data Shape:** Decision inputs are only `scope` ("personal"|"team"), `createdBy`, `is_admin`, plus a graph lookup `get_user_accessible_team_app_ids(user_id)` returning the set of team-app ids reachable by direct-or-team edge.

### Decisive source
```python
# MUTATION gate: creator OR admin only
if connector_scope == ConnectorScope.TEAM.value:
    return is_admin or created_by == user_id
if connector_scope == ConnectorScope.PERSONAL.value:
    return created_by == user_id          # admin gets NOTHING on others' personal

# VIEW gate: mirrors LIST visibility
if scope == ConnectorScope.TEAM.value:
    if is_admin or created_by == user_id:
        return True
    accessible = await graph_provider.get_user_accessible_team_app_ids(user_id)
    return connector_id in accessible     # any member who can reach it can see stats
```

**Flow:** personal scope: creator-only for BOTH gates (admin excluded — deliberate). Team scope: mutations need creator/admin; views additionally accept anyone holding an ORG_APP_RELATION-derived accessible-app id. Unknown scope ⇒ False both ways; exception ⇒ False (closed on error).
**Invariant:** View ⊇ Access for team scope, and view==access==creator-only for personal scope. The comment pins intent: "if a user can see a connector, they can see its stats" — keep stats endpoints on the VIEW gate or users lose visibility they legitimately had in listings.
**Probe:** `grep -c 'get_user_accessible_team_app_ids' app/connectors/core/registry/connector_registry.py` → `1`; suite `tests/unit/connectors/core/test_connector_registry.py::TestCanAccessConnector` (:279-359) covers all five polarity cases incl. `test_personal_scope_admin_no_access`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "can_user_view_connector get_user_accessible_team_app_ids", limit: 3 });
```
**Verdict:** Adopt the asymmetric pair + closed-on-error default; adapt the edge query to the host graph; omit the Arango-specific collection names.
