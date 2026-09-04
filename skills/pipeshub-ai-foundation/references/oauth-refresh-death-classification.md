<!-- capsule-v2 -->
# Refresh-token death classification — which provider errors mean "re-auth required" vs transient, across Google/Microsoft/ServiceNow dialects?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When an OAuth refresh POST fails, how does the platform decide this token is DEAD (deactivate connector) versus retry-later — without misclassifying WAF 403s?

## Marker-list classifier + ServiceNow special case
**Path/Symbol:** `backend/python/app/connectors/core/base/token_service/oauth_service.py:` `RefreshTokenInvalidError` (:32-34), `_PERMANENT_REFRESH_ERROR_MARKERS` (:37-44), `_is_permanent_refresh_rejection` (:47-49), `_is_servicenow_refresh_rejection` (:52-63), `refresh_access_token` (:339-395).
**Signature:** `async def refresh_access_token(self, refresh_token: str) -> OAuthToken` raising `RefreshTokenInvalidError` (permanent) or plain Exception (transient); ServiceNow check gated on `"oauth_token.do" in token_url` AND status 401 AND body contains both "server_error" and "access_denied".
**Data Shape:** Markers tuple: `invalid_grant / refresh_token is invalid / refresh token is invalid / refresh token has expired / invalid_refresh_token / bad_refresh_token` (lowercased substring match over the error STRING, since providers bury JSON in exception text).

### Decisive source
```python
except Exception as e:
    error_str = str(e)
    if _is_permanent_refresh_rejection(error_str) or \
       _is_servicenow_refresh_rejection(error_str, self.config.token_url):
        raise RefreshTokenInvalidError("Refresh token rejected by provider — expired or revoked; ...") from e
    status_match = re.search(r"status (\d+)", error_str)
    # Bare 403 stays transient — may be a WAF block, not a dead token
    if status_match and int(status_match.group(1)) == HttpStatusCode.FORBIDDEN.value:
        raise Exception(f"Token refresh failed with 403 Forbidden. This usually means ... {error_str}") from e
    raise
...
if not token.refresh_token:
    token.refresh_token = refresh_token   # Google omits it on refresh; Atlassian ROTATES it
```

**Flow:** classify error string → permanent ⇒ typed error consumed by TokenRefreshService's three-strikes ladder; 403 re-raised with explanatory text but NOT typed-dead (comment pins the WAF rationale); anything else propagates. On SUCCESS, missing refresh_token is back-filled with the old one (Google no-rotation) while a NEW returned one wins (Atlassian rotation) — one branch serving both dialects.
**Invariant:** Classification is string-marker based BECAUSE provider SDKs raise opaque wrapped errors; adding a provider means extending markers, never catching around call sites. Bare 403 must remain transient. Refresh-token preservation-vs-rotation is decided by response content alone — callers need no per-provider flags.
**Probe:** `grep -c '_PERMANENT_REFRESH_ERROR_MARKERS = (' app/connectors/core/base/token_service/oauth_service.py` → `1`; `grep -c '_is_servicenow_refresh_rejection' app/connectors/core/base/token_service/oauth_service.py` → `2`; direct tests `tests/unit/connectors/test_oauth_service.py` :967/:985 (`invalid_grant` raises typed) /:982/:1029 (non-permanent stays untyped) /:927 `test_refresh_preserves_old_refresh_token` — GREEN in battery (91 tests).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "RefreshTokenInvalidError invalid_grant refresh_access_token", limit: 3 });
```
**Verdict:** Adopt marker-classifier + 403-transient ruling + preserve-or-rotate backfill verbatim; adapt marker list per providers hosted.
