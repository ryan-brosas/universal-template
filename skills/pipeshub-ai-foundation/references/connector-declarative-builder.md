<!-- capsule-v2 -->
# Connector declarative builder — how does a vendor integration become a validated, self-registering connector definition at import time?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336` (`git log -1 --format=%H` = c28d133602543bd737b9791db84b76c5dee84ff7); Codebase Memory project `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When porting a new SaaS connector, what must run at class-definition time so the connector shows up in catalogs AND fails fast on incomplete auth config — without any runtime registration step?

## Declarative decorator DSL over a two-layer builder
**Path/Symbol:** `backend/python/app/connectors/core/registry/connector_builder.py:` `ConnectorBuilder.build_decorator` (:539-585), `_validate_oauth_requirements` (:594-661), `ConnectorConfigBuilder._reset` (:31-100); `registry/connector.py:Connector` decorator (:56-107).
**Signature:** `ConnectorBuilder(name) -> .in_group/.with_auth([AuthBuilder...])/.with_scopes([...])/.configure(fn)/.build_decorator() -> Callable[[type], type]`; `CommonFields.client_id/client_secret/api_token/base_url` factory fields.
**Data Shape:** Builder mutates a nested plain-dict config (`auth.schemas[authType].fields[]`, `auth.oauthConfigs[authType]`, `sync.supportedStrategies[]`, `filters.{sync,indexing}.schema.fields[]`). `build()` deepcopies and resets; `build_decorator()` returns a decorator that stamps `_connector_metadata` + `_is_connector=True` onto the decorated class.

### Decisive source
```python
# connector_builder.py — build_decorator(): config frozen BEFORE decorator runs,
# OAuth configs auto-registered under the FINAL name (rename-safe)
config = self.config_builder.build()
if self.permission_model is not None:
    config["permissionModel"] = self.permission_model.value
oauth_registry = get_oauth_config_registry()
for auth_type, oauth_config in self._oauth_configs.items():
    if oauth_config.connector_name != self.name:
        old_config = oauth_registry.get_config(oauth_config.connector_name)
        if old_config is oauth_config:
            del oauth_registry._configs[oauth_config.connector_name]
        oauth_config.connector_name = self.name
    ...
    oauth_registry.register(oauth_config)   # overwrite allowed → toolset/connector sharing
for auth_type in self.supported_auth_types:
    if auth_type and auth_type.upper() == "OAUTH":
        self._validate_oauth_requirements(config, auth_type)
self._validate_required_auth_fields(config)
```

**Flow:** import-time chain evaluation → `.with_auth(AuthBuilder...)` splits per-auth-type into `schemas` + stores `OAuthConfig`s for later registration → `.configure(lambda)` applies icon/docs/sync knobs → `.build_decorator()` freezes config dict, re-points every OAuthConfig to the final connector name (deleting only ITS OWN stale entry), backfills icon/app_group/categories/doc-links onto the OAuthConfig, then validates: OAUTH types require authorizeUrl+tokenUrl+non-empty scopes+schema redirectUri, else **ValueError raised at import time**.
**Invariant:** Validation happens at MODULE IMPORT, not at request time — an incomplete OAuth connector crashes process startup (fail-fast), never surfaces as a mid-request 500. Required-field validation checks field *definitions* (`required=True` ⇒ has a `name`), never values; values are runtime config.
**Probe:** `grep -c 'OAuth configuration incomplete for connector' app/connectors/core/registry/connector_builder.py` → `1`; `bash -c 'cd backend/python && /tmp/psh17venv/bin/python -m pytest tests/unit/connectors/core/test_connector_builder.py tests/unit/connectors/core/test_connector_registry.py -q'` → 175 passed (64+111).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "build_decorator validate_oauth_requirements", limit: 5 });
```
(line-exact: `connector_builder.py` builder methods.)

## Verdict
Adopt the two-layer shape: outer `ConnectorBuilder` (identity/auth/scopes) + inner `ConnectorConfigBuilder` (serializable UI schema dict), import-time fail-fast validation, and OAuth-config auto-registration keyed by final name (enables one OAuth app shared by connector + toolset). Adapt the config dict keys to host schema conventions. Omit the specific Slack/Google catalog instances in `registry/connector.py` (654L of pure declarations — copy the pattern, not the entries).
