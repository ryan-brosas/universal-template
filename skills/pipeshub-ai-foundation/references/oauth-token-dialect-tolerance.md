<!-- capsule-v2 -->
# Token-endpoint dialect tolerance — how do you parse token responses when half the providers ignore the JSON spec?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What content-type ladder and error taxonomy must a token exchange/refresh client implement so form-encoded responders (GitHub-style) don't silently break background refresh?

## One shared exchange, JSON-or-form parsing, two-level error taxonomy
**Path/Symbol:** `backend/python/app/agents/mcp/oauth_client.py:_parse_token_response/_parse_form_encoded/_post_token_request/exchange_code_for_token/refresh_access_token` (L43–151).
**Signature:** `exchange_code_for_token(token_url, client_id, client_secret?, code, redirect_uri, code_verifier?) -> OAuthTokens`; `refresh_access_token(token_url, client_id, client_secret?, refresh_token) -> OAuthTokens`; `_post_token_request(token_url, data) -> dict`.
**Data Shape:** Returns `OAuthTokens{access_token, token_type="Bearer", refresh_token?, expires_in?, scope?, token_url, created_at}` — `token_url` is persisted ON the tokens so refresh never re-discovers.

### Decisive source
```python
_PERMANENT_REFRESH_ERROR_MARKERS = (
    "invalid_grant", "invalid_refresh_token", "refresh token is invalid",
    "refresh token has expired", "bad_refresh_token",
)

def _parse_token_response(content_type, text, json_body):
    if json_body is not None: return json_body                       # declared JSON wins
    if "application/x-www-form-urlencoded" in ct or "text/plain" in ct:
        return _parse_form_encoded(text)                             # GitHub-style form
    # Declared type matched neither — try JSON, FALL BACK to form anyway.
    try: return _json.loads(text)
    except Exception: return _parse_form_encoded(text)

# ≥400 → classify body text FIRST:
if _is_permanent_refresh_rejection(text):
    raise MCPRefreshTokenInvalidError(...)   # subclass of MCPOAuthError ⇒ re-auth required
raise MCPOAuthError(...)
```
Module docstring records the bug this module exists to kill: the reference PR duplicated this logic and "its background path only parsed JSON responses, silently breaking for form-encoded token endpoints (e.g. GitHub)". One shared implementation serves BOTH the initial code-exchange route AND the background sweep.

**Flow:** POST with `Accept: application/json` + 15s timeout → on ≥400 classify permanent-rejection markers before generic OAuth error → parse by content-type ladder (declared-JSON → declared-form/text-plain → sniffed JSON → form fallback) → require `access_token` else `MCPOAuthError` → fill defaults (`token_type` falls back to `"Bearer"`; refresh keeps the OLD `refresh_token` when the provider doesn't rotate: `token_data.get("refresh_token") or refresh_token`).
**Invariant:** (1) Never trust declared content-type alone — unknown types get a JSON-then-form double attempt; form parsing uses `parse_qs(..., keep_blank_values=True)` and coerces numeric `expires_in` best-effort. (2) Permanent rejection is a DISTINCT exception type so callers can force re-authentication instead of retrying forever; it subclasses the generic error for backward compatibility. (3) Refresh preserves the previous refresh token unless a new one arrives — dropping it would orphan every later refresh against non-rotating providers. (4) Missing `access_token` in a 2xx body is still an error.
**Probe:** `tests/unit/agents/mcp/test_oauth_client.py` (305L): parses_basic_fields :40; non_numeric_expires_in_left_unparsed :46; json_response :57; **form_encoded_response** :76; missing_access_token_raises :94; error_status_raises_oauth_error :110; includes_code_verifier_when_provided :126; unknown_content_type_falls_back_to_json_body :146.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "_parse_token_response MCPRefreshTokenInvalidError refresh_access_token" --detail ids
```

## Verdict
Adopt the four-rung parse ladder, the marker-based permanent-vs-transient error taxonomy, and refresh-token carry-forward; keep one shared implementation for both call sites. Adapt timeout and provider marker list to the host's provider set. Omit PipesHub's FastAPI route wrappers.
