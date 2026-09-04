<!-- capsule-v2 -->
# Catalog listing filters — which connectors does a given caller actually see in "add a connector" (beta × account-type × scope matrix)?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Porting the marketplace list: how do feature flag, enterprise accounts, and personal/team scope combine to filter beta connector types, and what must the pagination counts include?

## Beta visibility is a 2×2×scope product, evaluated BEFORE search
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_registry.py:` `get_all_registered_connectors` (:690-860), `_get_beta_connector_names` (:224-246), `_normalize_connector_name` (:220-222); `factory/connector_factory.py:_beta_connector_definitions` (:141-150).
**Signature:** `async def get_all_registered_connectors(self, *, is_admin: bool, scope: str | None = None, page=1, limit=20, search=None, account_type=None) -> dict` returning `{connectors[], pagination{}, registryCountsByScope}`.
**Data Shape:** Beta set = keys of `ConnectorFactory._beta_connector_definitions` (calendar/meet/forms/slides/docs/zendesk/airtable), normalized via `name.replace(' ','').lower()`; `registryCountsByScope = {"personal": N, "team": M}`.

### Decisive source
```python
if not beta_enabled and is_beta_connector:
    continue                                  # flag off hides betas everywhere
# Beta connectors are allowed for:
# - personal scope in enterprise accounts
# - team scope in individual accounts
if is_beta_connector and account_type and \
   account_type.lower() in ['enterprise', 'business'] and \
   scope == ConnectorScope.TEAM.value:
    continue                                  # the ONLY cell excluded
```

**Flow:** refresh feature flag once (`ENABLE_BETA_CONNECTORS`, fail-OPEN to all-connectors on error) → collect normalized beta names from factory (single source of truth) → per registered type: scope filter → beta/flag filter → enterprise-team exclusion → hidden-connector skip (`hideConnector`) → tokenized AND substring search over name/type/group/description/authTypes/categories → paginate in Python → compute `registryCountsByScope` AFTER flag/beta/hidden filters but BEFORE search.
**Invariant:** Enterprise exclusion applies ONLY at team scope (instability quarantined away from shared org surfaces) — porting it as global would break personal beta trials for enterprise users. Counts exclude search so UI can show "3 of 42" while searching. Feature-flag failure fails OPEN (list everything) rather than blanking the marketplace.
**Probe:** `grep -cF "account_type.lower() in ['enterprise', 'business']" app/connectors/core/registry/connector_registry.py` → `1`; `bash -c 'cd backend/python && /tmp/psh17venv/bin/python -m pytest tests/unit/connectors/core/test_connector_registry_extended.py tests/unit/connectors/test_connector_factory.py -q'` → green (41+31 tests).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "get_all_registered_connectors beta enterprise pagination", limit: 3 });
```
**Verdict:** Adopt the filter ORDER (scope→beta→account→hidden→search→paginate→counts) and fail-open flag handling; adapt flag/account-type plumbing; omit concrete beta definitions.
