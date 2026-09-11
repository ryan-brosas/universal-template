<!-- capsule-v2 -->
# Proxy auth header ladder — How do you send credentials upstream without leaking your own transport state back to clients?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How does a proxy choose between bearer keys, browser sessions, stored OAuth tokens, and Entra tokens per connection — and which response headers must never pass back through?

## Credential selection + response header hygiene seam
**Path/Symbol:** `backend/open_webui/routers/openai.py:get_headers_and_cookies` (156-219), `_clean_proxy_headers` + `_STRIP_PROXY_HEADERS` (76-87); `backend/open_webui/utils/headers.py:include_user_info_headers` (37-62), `_mint_forward_user_jwt` (23-34), `get_custom_headers` (87-89).
**Signature:** `async def get_headers_and_cookies(request, url, key=None, config=None, metadata=None, user=None) -> tuple[dict, dict]`; `def include_user_info_headers(headers: dict, user=None) -> dict`; `def get_custom_headers(custom_headers: dict, user=None, metadata=None, request=None) -> dict`.
**Data Shape:** config.auth_type ∈ {'bearer'(default)|'none'|'session'|'system_oauth'|'azure_ad'|'microsoft_entra_id'}; returns (headers, cookies).

### Decisive source
```python
    if auth_type == 'bearer' or auth_type is None:
        token = f'{key}'
    elif auth_type == 'none':
        token = None
    elif auth_type == 'session':
        cookies = request.cookies
        token = request.state.token.credentials
    elif auth_type == 'system_oauth':
        cookies = request.cookies
        oauth_token = None
        try:
            if request.cookies.get('oauth_session_id', None):
                oauth_token = await request.app.state.oauth_manager.get_oauth_token(
                    user.id, request.cookies.get('oauth_session_id', None))
        except Exception as e:
            log.error(f'Error getting OAuth token: {e}')
        if oauth_token:
            token = f'{oauth_token.get("access_token", "")}'
    elif auth_type in ('azure_ad', 'microsoft_entra_id'):
        token = get_microsoft_entra_id_access_token()
```

```python
_STRIP_PROXY_HEADERS = frozenset({'Content-Encoding', 'Content-Length', 'Transfer-Encoding'})
```

**Flow:** base headers (+ OpenRouter referer/title pair when host matches) → optional user-info forward (signed HS256 JWT with sub/email/name/role/iss/exp when a forward secret is configured; mint failure falls back to legacy plain X-OpenWebUI-User-* headers) → auth_type ladder picks token/cookies → custom template headers applied last. On the way BACK, every streamed/buffered response passes `_clean_proxy_headers`, dropping exactly the three stale-encoding headers.
**Invariant:** unspecified auth_type must behave as bearer; system_oauth fails OPEN (logs, proceeds without token) rather than failing the chat; forwarded identity is either signed or URL-quote-sanitized, never raw-trusted by the backend; Content-Encoding/Length/Transfer-Encoding can never cross the proxy boundary because aiohttp already decompressed the body (client ZlibError otherwise — aiohttp issue 4462).
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "_STRIP_PROXY_HEADERS = frozenset" backend/open_webui/routers/openai.py` → line 80; `grep -n "auth_type == 'session'" backend/open_webui/routers/openai.py` → line 190.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_headers_and_cookies include_user_info_headers _mint_forward_user_jwt custom headers", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves all cited symbols in both files.

## Verdict
Adopt: auth_type enum ladder with bearer default and fail-open OAuth exchange, JWT-vs-legacy identity forwarding fallback, three-header strip set. Adapt: template placeholder vocabulary (`{{CHAT_ID}}`…`{{USER_AGENT}}`) to host metadata; groups fetch is lazily gated on placeholder presence (`custom_headers_require_user_groups`). Omit: OpenRouter-specific referer branding. Caveat: zero direct tests upstream; `_clean_proxy_headers` is duplicated verbatim in both routers (ollama.py 63-65) — keep them in sync when porting.
