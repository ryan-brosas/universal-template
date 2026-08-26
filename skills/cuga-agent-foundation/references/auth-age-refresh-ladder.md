<!-- capsule-v2 -->
# Age-based token refresh without JWT decoding — how do you keep auto-injected auth tokens fresh when token TTLs are random and unreadable?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your tokens have a random 10–30 min TTL you can't (or won't) decode — how do you guarantee the auto-injected `file_system` token never goes stale mid-task without re-login storms?

## Refresh by AGE (9-min floor), fall back to the stale token on any failure
**Path/Symbol:** `src/cuga/backend/tools_env/registry/registry/authentication/base_auth_manager.py` — `REFRESH_AFTER_SECONDS = 9 * 60` :11 (with TTL math in docstring :5-10), `_store` :20-22, `_is_stale` :24-27, `get_access_token` :29-57, `refresh_stale` :59-67, `clear_tokens` :69-72, `get_stored_tokens` :78-84 (the refresh chokepoint).
**Signature:** `get_access_token(app_name) -> Optional[str]`; `get_stored_tokens() -> dict` — refreshes stale entries FIRST, then returns the live map; abstract hooks `_get_credentials(app_name)` / `_fetch_token(app_name, creds)`.
**Data Shape:** two parallel dicts: `_tokens[app] = str`, `_token_times[app] = wall-clock fetch time`. Staleness = no timestamp OR `now - ts >= 540s`.

### Decisive source
```python
# :51-57 — a failed refresh must NOT error an in-flight call
except Exception:
    # A stale token may still be valid (TTL is up to 30 min) — prefer it over
    # erroring so an in-flight call can still try. Only re-raise (preserving
    # the detailed message) when we have nothing to fall back on.
    if stored_token: return stored_token
    raise
```
**Flow:** get → fresh? return stored → stale/missing: fetch creds (None ⇒ return whatever we had, same contract as before) → `_fetch_token` → store WITH timestamp → on exception: stale-token fallback, else raise. `get_stored_tokens` is the chokepoint feeding the `_tokens` header (which carries file_system's token into every cross-app call), so refreshing there keeps the auto-injected token fresh without the agent ever seeing it.
**Invariant:** (1) 9 min < 10-min guaranteed TTL floor ⇒ age-based re-fetch is ALWAYS valid at refresh time — no exp decoding needed; tokens that drew 30 min just re-login early (cheap). (2) Refresh failure NEVER raises while ANY prior token exists. (3) Direct `_store` (the /auth/token sniff path) records time too, so sniffed tokens aren't instantly stale. (4) Subclass AppWorldAuthManager adds lazy supervisor profile/passwords with one-shot retry + loud boxed HTTP diagnostics + `TokenFetchError(status_code, response_body, url)` carrying server `message`/`detail` for user-facing errors.

**Probe:** `src/cuga/backend/tools_env/registry/tests/test_auth/test_token_refresh.py` — `test_fresh_token_is_reused` (:41), `test_stale_token_is_refreshed` (:48), `test_refresh_failure_falls_back_to_stale_token` (:56), `test_no_credentials_returns_none_without_error` (:65), `test_get_stored_tokens_refreshes_stale_entries` (:70), `test_direct_store_records_time` (:80).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "get_access_token stale REFRESH_AFTER_SECONDS _token_times get_stored_tokens", limit: 8 });
```
## Verdict
Adopt age-based refresh wherever token introspection is unavailable and TTL has a known floor (set threshold < floor). Adapt the subclass split (base lifecycle vs provider-specific credential lookup). Omit the multi-app map only for single-service clients.
