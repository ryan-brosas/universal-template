<!-- capsule-v2 -->
# Refresh-race lock + client resolution ladder — why do three independent refresh callers share ONE keyed lock dict, and which OAuth client wins?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you serialize token refresh across a REST route, a background sweep, and the agent loop's on-demand path — and in what order do legacy-DCR / shared-DCR / static clients resolve?

## defaultdict(asyncio.Lock) keyed by (instance_id, owner_id)
**Path/Symbol:** `backend/python/app/agents/mcp/token_refresh.py:_refresh_locks/resolve_client_credentials/refresh_credential_record/_refresh_credential_record_locked` (L48–139); constants `agents/constants/mcp_server_constants.py:get_mcp_dcr_client_path/get_mcp_shared_dcr_client_path/get_mcp_oauth_client_config_path/get_mcp_credentials_path`.
**Signature:** `resolve_client_credentials(instance_id, owner_id, config_service) -> tuple[Optional[str], Optional[str]]`; `refresh_credential_record(instance_id, owner_id, config_service) -> OAuthTokens`.
**Data Shape:** Credential record at `/services/mcp/credentials/{instance_id}/{owner_id}` carries `oauthTokens{refreshToken|refresh_token, tokenUrl|token_url, ...}` plus `updatedAt`; both snake_case and camelCase keys accepted on read.

### Decisive source
```python
# Keyed by (instance_id, owner_id) so THREE callers serialize against EACH
# OTHER, not just themselves: the /oauth/refresh route, MCPTokenRefreshService's
# background sweep, and agent_loop/mcp_session.py::_refresh_and_reopen.
# Without this: two callers race on an expired token, BOTH read the same
# still-valid refresh token, both hit the token endpoint, and — with a provider
# that ROTATES refresh tokens — the loser's write silently clobbers the winner's
# freshly-issued tokens with a refresh token the provider already invalidated.
_refresh_locks = defaultdict(asyncio.Lock)   # never evicted; unbounded but slow-growing

async def resolve_client_credentials(...):
    dcr = await config.get_config(get_mcp_dcr_client_path(instance_id, owner_id), default=None)
    if isinstance(dcr, dict) and dcr.get("clientId"): return dcr["clientId"], dcr.get("clientSecret")
    shared = await config.get_config(get_mcp_shared_dcr_client_path(instance_id), default=None)
    if isinstance(shared, dict) and shared.get("clientId"): return ...
    static = await config.get_config(get_mcp_oauth_client_config_path(instance_id), default=None)
    return static.get("clientId"), static.get("clientSecret")   # may be (None, None)

record = await config.get_config(cred_path, default=None, use_cache=False)  # FRESH read under lock
...
record["oauthTokens"] = new_tokens.model_dump(by_alias=True, mode="json")
record["updatedAt"] = get_epoch_timestamp_in_ms()
await config.set_config(cred_path, record)      # full-record write-back
```
Error split: `MCPTokenRefreshError(ValueError)` for pre-flight gaps (no record / no refresh token / no persisted tokenUrl / no resolvable client — "none of these reach the token endpoint at all"); `MCPOAuthError`/`MCPRefreshTokenInvalidError` propagate UNCHANGED from the HTTP layer. The ValueError base keeps compatibility with tests written against the pre-refactor bare raise.

**Flow:** acquire `(instance_id, owner_id)` lock → read credential record with cache OFF → validate refresh token + persisted tokenUrl present → resolve client via per-owner DCR → shared per-instance DCR → admin-static ladder → call shared `refresh_access_token` → write full record back with camelCase tokens + fresh `updatedAt`.
**Invariant:** (1) The lock key includes the OWNER, not just the instance — two users of one MCP server refresh concurrently without blocking. (2) The credential read must bypass the config cache (`use_cache=False`) or the lock serializes around stale data and the race it exists to kill comes back. (3) Legacy per-owner DCR client resolves FIRST so already-issued tokens keep refreshing against the exact client they were minted against; provider-side client identity changes invalidate grants. (4) Locks are never evicted — deliberate, matching sibling services' per-path lock dicts. (5) Pre-flight failures are typed separately from HTTP failures so callers know whether re-authentication can even help.
**Probe:** `tests/unit/agents/mcp/test_token_refresh.py` (182L): prefers_dcr_client :32; falls_back_to_shared_client :48; falls_back_to_static :67; no_client_returns_none_none :82; missing_record/refresh_token/token_url/non_dict_tokens/client raises :91–:119; successful_refresh_persists_new_tokens :133; permanent_rejection_propagates :162.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "_refresh_locks resolve_client_credentials refresh_credential_record get_mcp_credentials_path" --detail ids
```

## Verdict
Adopt the cross-caller `(instance, owner)`-keyed lock dict, the cache-bypassing read-under-lock, the three-tier client resolution order, and the two-level error split. Adapt the config-path scheme and epoch-ms timestamps to the host. Omit the background sweep scheduling itself (`mcp_token_refresh_service.py` product wiring).
