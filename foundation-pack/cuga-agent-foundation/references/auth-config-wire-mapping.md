<!-- capsule-v2 -->
# Declarative auth-to-wire mapping — how do you turn an auth config object into headers/query params without leaking secrets into logs or dropping existing values?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your tool configs declare `Auth(type, key, value)` — what's the exact mapping to the wire for bearer/basic/header/api-key/query, and which silent no-ops must you preserve?

## Five types, three carriers; every malformed input is a logged NO-OP, never a raise
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/adapter.py` — `apply_authentication(auth, headers, query_params)` :558-598. Direct suite: `src/cuga/backend/tools_env/registry/tests/test_auth/test_apply_authentication.py` (16 tests).
**Signature:** `apply_authentication(auth: Auth | None, headers: dict, query_params: dict) -> None` (mutates in place; returns nothing).
**Data Shape:** `Auth(type: str, value: str|None, key: str|None)`; carrier per type: bearer/basic → `headers['Authorization']`; header → `headers[auth.key]`; api-key/query → `query_params[key or 'api_key']`.

### Decisive source
```python
# :567-579 guards + secret resolution BEFORE any branch
if not auth or not auth.value: return          # no-auth / empty-value = no-op
value = resolve_secret(auth.value)             # vault:// / env refs resolved here
if not value: return                           # resolution failure = silent no-op
auth_type = auth.type.lower()                  # 'BEARER'/'Bearer' work (:173-191)
# :583-594 basic requires 'user:pass' — else warn + skip; header REQUIRES key
if auth_type == 'basic':
    if ':' in value: headers['Authorization'] = f"Basic {base64.b64encode(value.encode()).decode()}"
    else: logger.warning("Basic auth requires 'username:password' format in value")
elif auth_type == 'header':
    if auth.key: headers[auth.key] = value
    else: logger.warning("Header auth requires 'key' field to specify header name")
```
**Flow:** guard (None/value-less → untouched dicts) → resolve_secret → lower-case type → five-way branch fills exactly ONE carrier → unknown types are silent no-ops. Existing headers/query params are always preserved (only the auth key is written).
**Invariant:** (1) Never raise on bad config — a misconfigured app degrades to unauthenticated with a warning, so one broken tool can't kill registry startup. (2) Secret VALUES never appear in warnings. (3) api-key and query share the query-param carrier with default key `api_key`. (4) Resolution happens at CALL time, not config-load time — rotating a vault secret takes effect without reload.

**Probe:** `tests/test_auth/test_apply_authentication.py` — `test_bearer_auth` (:16), `test_basic_auth_invalid_format` (:39), `test_header_auth_without_key` (:61), `test_api_key_auth_with_custom_key` (:83), `test_unknown_auth_type` (:138), `test_preserves_existing_headers` (:149), `test_case_insensitive_auth_type` (:173).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "apply_authentication bearer basic api-key query headers", limit: 8 });
```
## Verdict
Adopt the mutate-in-place five-type ladder for any pluggable auth config. Keep the no-op-not-raise contract. Omit resolve_secret only if your values are literal (then add it before you add vaults).
