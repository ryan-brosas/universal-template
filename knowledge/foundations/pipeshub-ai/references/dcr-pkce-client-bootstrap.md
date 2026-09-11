<!-- capsule-v2 -->
# DCR + PKCE client bootstrap — how do you register an OAuth client on the fly for a custom MCP server and keep refresh working without re-discovery?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What must RFC 7591 dynamic registration persist onto the client record so every later authorization and background refresh works, and what does the PKCE/state helper trio look like?

## register_dynamic_client stores the endpoint pair ON the client
**Path/Symbol:** `backend/python/app/agents/mcp/dcr.py:register_dynamic_client/generate_code_verifier/generate_code_challenge/generate_state/build_authorization_url` (L65–256); `agents/mcp/models.py:DCRClient` (L207–217).
**Signature:** `register_dynamic_client(registration_endpoint: str, redirect_uri: str, authorization_url: str, token_url: str, client_name: str = "PipesHub") -> DCRClient`; `generate_code_verifier(n=64)`; `generate_code_challenge(verifier)`; `build_authorization_url(authorization_url, client_id, redirect_uri, state, scopes=None, code_challenge=None)`.
**Data Shape:** `DCRClient{client_id, client_secret?, registration_access_token?, registration_client_uri?, authorization_url, token_url, registered_at_epoch_ms}` — the `authorization_url`/`token_url` arguments come from discovery (or static config) and are STORED on the returned client.

### Decisive source
```python
await assert_discovery_target_allowed(registration_endpoint)   # SSRF gate BEFORE any request
payload = {
    "client_name": client_name,
    "redirect_uris": [redirect_uri],
    "grant_types": ["authorization_code", "refresh_token"],   # BOTH grants up front
    "response_types": ["code"],
    "token_endpoint_auth_method": "client_secret_post",
}
# ≥400 → DCRError(status + body text); network failure → DCRError("...request failed")
# missing client_id in a 2xx → DCRError("DCR response missing client_id")

def generate_code_verifier(n=64):  return b64url(os.urandom(n)).rstrip("=")
def generate_code_challenge(v):    return b64url(sha256(v.encode()).digest()).rstrip("=")
def generate_state():              return secrets.token_urlsafe(32)
# build_authorization_url: scope joined with SPACES; when challenge present also
# sets code_challenge_method="S256"; urlencode(params) appended after "?".
```
Why endpoints ride the client record (module docstring): "background token refresh never needs to re-discover metadata" — `DCRClient.token_url` is exactly what `refresh_credential_record` later reads as the persisted `tokenUrl`.

**Flow:** SSRF-check registration endpoint → POST the fixed grant/response payload → require `client_id` in the response → wrap result with caller-supplied authorization/token URLs → authorize flow builds the redirect URL from those endpoints with optional PKCE S256 → tokens come back through the shared exchange (`oauth_client.py`) which persists `token_url` next to the tokens.
**Invariant:** (1) Registration is rejected BEFORE any network I/O if the target fails the public-URL policy. (2) `grant_types` must include `refresh_token` at registration time — a client registered without it cannot be refreshed later regardless of stored tokens. (3) PKCE verifier is unpadded url-safe base64 of 64 random bytes; challenge is its SHA-256, method pinned to S256 whenever present. (4) Registration errors are typed (`DCRError`) with status/body preserved — never bare raises.
**Probe:** `tests/unit/agents/mcp/test_dcr.py`: successful_registration_returns_dcr_client :331; error_status_raises_dcr_error :357; missing_client_id_raises :374; network_error_wrapped :391; blocked_registration_target_raises_before_any_request :405; build_authorization_url includes_required_params :424 / scopes :436 / omits_scope :446 / pkce :455 / omits_pkce :466.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "register_dynamic_client generate_code_verifier build_authorization_url DCRClient" --detail ids
```

## Verdict
Adopt the store-endpoints-on-the-client pattern (refresh independence), both-grants-up-front payload, pre-request SSRF check, and the S256 PKCE trio. Adapt client_name default and redirect storage to the host. Omit the PipesHub route layer that drives the authorize round-trip.
