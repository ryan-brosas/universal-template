<!-- capsule-v2 -->
# Error-dict tool-call contract — how does a tool gateway return provider HTTP failures to an LLM without raising, and how do you surface the server's real error message?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When an upstream API 401s/500s mid-tool-call, what should the agent's tool layer return so the LLM can react — and which response-body fields carry the honest message?

## status:"exception" dicts instead of exceptions; message ← body.message → body.detail → whole-body
**Path/Symbol:** `src/cuga/backend/tools_env/registry/registry/api_registry.py` — `call_function(app_name, function_name, arguments, auth_config=None)` :196-471: oauth2 header injection :229-297 (TokenFetchError detail dict :262-273), `_tokens` cross-app header :305-306, /auth/token response sniffing :316-363, `httpx.HTTPStatusError` ladder :366-441, generic-exception fallback :442-471; web-search virtual app :183-224.
**Signature:** success → `list[TextContent(text=json)]`; ANY failure → `{"status": "exception", "status_code": int, "message": str, "error_type": type(e).__name__, "function_name": str, "error_detail": {...}}`.
**Data Shape:** the FastAPI layer (`api_registry_server.call_mcp_function` :380-415) turns that dict into `JSONResponse(status_code=result["status_code"])`, and REWRITES `message` from `error_detail.response_body`: dict ⇒ `message` field, else `detail`, else stringified; string ⇒ as-is.

### Decisive source
```python
# :411-432 — extract the HONEST message from the provider's own body
detailed_message = None
response_body = error_detail.get('response_body')
if isinstance(response_body, dict):
    if "message" in response_body: detailed_message = response_body["message"]
    elif "detail" in response_body: detailed_message = response_body["detail"]
    else: detailed_message = json.dumps(response_body, indent=2)
elif isinstance(response_body, str): detailed_message = response_body
```
**Flow:** secure app? resolve oauth2 token into `Authorization: Bearer` (TokenFetchError → exception-dict with embedded status/url/body) → inject `_tokens: json(all stored tokens)` for cross-app auth → `mcp_client.call_tool` → on HTTPStatusError capture {status,url,method,response_body,request_body,headers}, log loudly, build exception-dict → on any other Exception same shape with status 500. AppWorld benchmark additionally sniffs `/auth/token` responses and `_store`s returned access_tokens (with fetch time) back into the auth manager.
**Invariant:** (1) NEVER raise through to the caller — every failure is a structured dict the LLM can read and retry differently. (2) The user-visible `message` must be the PROVIDER'S message/detail, never a generic wrapper — surface it or agents loop on useless errors. (3) Secrets redact from logs (`password=***` reconstruction). (4) Virtual apps (web search) live INSIDE call_function behind the same contract.

**Probe:** No direct unit suite at HEAD for api_registry.py (coverage caveat — exercised via e2e helpers `tools_env/registry/tests/e2e_helpers.py` + test_api_registry_error_handling.py); auth-fallback behavior pinned by test_token_refresh.py at the manager layer.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "call_function status exception status_code detailed_message TokenFetchError", limit: 8 });
```
## Verdict
Adopt the structured exception-dict over raise-through for any LLM-facing tool boundary; copy the message→detail→body precedence verbatim. Adapt field names to your envelope. Omit token sniffing unless you proxy login endpoints.
