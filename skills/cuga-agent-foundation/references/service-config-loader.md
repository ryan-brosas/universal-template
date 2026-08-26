<!-- capsule-v2 -->
# Service-config loader — why does a header sitting in `environment` silently become auth, and how is service type inferred when `type:` is absent?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Users paste standard MCP `mcpServers` YAML, legacy `services` lists — sometimes with credentials in the wrong field. How do you accept all of it and still route every service to the right transport + auth?

## Dual-format parse → type-inference ladder → env-header-to-auth promotion
**Path/Symbol:** `src/cuga/backend/tools_env/registry/config/config_loader.py` — models `Auth` :8-38 (five types: header/bearer/api-key/basic/query), `ApiOverride` :41-47, `ServiceConfig` :50-69 (url+command+args+env+cwd+transport+include+readiness quad), `load_service_configs` :82-136 (dual-format dispatch), DB twin `load_service_configs_from_db` :139-171, `_create_service_config` :174-265.
**Signature:** `load_service_configs(yaml_path) -> Dict[name, ServiceConfig]`; `"none"/"None"` path literal → `{}` = database mode. Type ladder in `_create_service_config`: explicit type → normalize aliases (`mcp|mcp_server|mcp-server`, `trm|tool-runtime-manager|tool_runtime_manager`, `openapi|open-api|open_api`) → else infer: `is_mcp_server` flag → has `command` → MCP_SERVER; has `tools` list → TRM; default OPENAPI.
**Data Shape:** YAML accepted at root: dict with `services:` (legacy list-of-dicts) AND/OR `mcpServers:` (standard MCP format) — both merged into one namespace; or bare legacy root list.

### Decisive source
```python
# config_loader.py:187-203 — env-header promotion: credentials in the WRONG field
# are rescued into auth for HTTP/SSE transports instead of being passed as process env
if env_config and not auth and isinstance(env_config, dict):
    # Check if this is likely an HTTP/SSE transport (has URL, no command)
    if config.get('url') and not config.get('command'):
        for key, value in env_config.items():
            if isinstance(value, str):
                if key.lower() in ['x-api-key', 'api-key', 'apikey', 'authorization']:
                    if key.lower() == 'authorization':
                        if value.startswith('Bearer '):
                            auth = Auth(type='bearer', value=value.replace('Bearer ', ''))
                        else:
                            auth = Auth(type='header', key='Authorization', value=value)
                    else:
                        auth = Auth(type='header', key=key, value=value)
                    break   # ← FIRST recognized header only
```
Why: stdio servers legitimately consume `env` as subprocess environment; but users copy HTTP-server snippets where those headers land uselessly in `env`. The promotion fires ONLY for URL-without-command services (real HTTP/SSE shape) and only on a known-header allow-list, keeping stdio `env` semantics untouched. Note the asymmetry it produces: same YAML key means "process env" for command services but "auth source" for url services.

**Flow:** read YAML → collect from both sections → per service: build `Auth` if present, else try env-promotion → resolve type via ladder → assemble `ServiceConfig` → attach `api_overrides` models. DB mode mirrors this by mapping stored tool rows through the SAME `_create_service_config` so downstream code never knows the config source.
**Invariant:** Never let an unrecognized key in `environment` crash loading — unknown headers are left as plain env (harmless for HTTP). Type inference order matters: `command` beats `tools` beats URL-default; an explicit-but-unknown type string falls back to shape-based inference rather than raising. `api_overrides` attach AFTER model construction because they're optional nested models.
**Probe:** direct tests `tests/test_legacy_openapi.py` (`load_service_configs` on legacy format :14/:27/:111), `tests/test_mixed_configuration.py` (:15/:49/:198 mixed services+mcpServers), naming e2e reuses the loader (`test_naming_strategy_e2e.py`). Coverage caveat: env-header promotion branch itself untested upstream — verify by reading :187-203.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "load_service_configs ServiceConfig _create_service_config mcpServers", limit: 10 });`

## Verdict
Adopt dual-format acceptance, the alias-normalizing type-inference ladder, and guarded env-header→auth promotion scoped to URL-shaped services. Adapt the allow-list to your credential conventions. Omit the DB twin if configs are file-only.
