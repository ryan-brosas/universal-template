<!-- capsule-v2 -->
# LLM models listing auth ladder — how does the /llm/models endpoint pick between draft-config keys, vault refs, custom auth headers, and env fallbacks without leaking secrets?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does `GET /llm/models` resolve credentials across force_env modes and auth_type variants, what URL normalization must LiteLLM proxies get, and what may logs echo?

## Draft config by default; force_env skips it; api_key field = vault-ref-or-plain; auth_header auto-Bearer; masked logging only
**Path/Symbol:** `src/cuga/backend/server/manage_routes/llm_routes.py:24-191` (`list_llm_models`); tables `_PROVIDER_MODELS_URL` :11-15, `_PROVIDER_API_KEY_REF` :17-21.
**Signature:** `async def list_llm_models(request, disable_ssl: bool = Query(False, alias="disable_ssl"), agent_id: Optional[str] = None) -> {models: sorted[str]}`.
**Data Shape:** providers groq|openai|litellm (else 400); litellm REQUIRES `url` in draft config → normalized: rstrip('/') then `/models` if already ends `/v1` else `/v1/models` (prevents `/v1/v1`). Auth result is either `headers[Authorization]=Bearer <key>` OR `headers[<auth_header_name>]=<custom>` — never both.

### Decisive source
```python
# llm_routes.py:115-137 and :160-170
api_key_ref = llm_cfg.api_key
if api_key_ref:
    if api_key_ref.startswith("vault://"):
        resolved = resolve_secret(api_key_ref)
        if resolved and not resolved.startswith("vault://"):
            api_key_ref = resolved        # success
        else:
            logger.error(f"Failed to resolve api_key from vault: {api_key_ref}")
            api_key_ref = None            # REFERENCE leaked to log, never the value
...
if auth_header_name.lower() == "authorization" and not api_key_ref.lower().startswith(
    _AUTH_SCHEMES                       # ("bearer ", "basic ", "token ", "digest ")
):
    custom_auth_header = f"Bearer {api_key_ref}"
...
masked_auth = custom_auth_header[:10] + "***" if len(...) > 10 else "***"
```
Mode selection: `force_env = bool(settings.secrets.force_env)` read defensively (getattr + try/except → False). When False, the DRAFT config (`load_draft(agent_id)`, default agent `cuga-default`) always wins; LLMConfig pydantic validation failure → 400. Env fallback ladder for non-auth_header mode when no key configured: `_PROVIDER_API_KEY_REF[provider]` (litellm maps to OPENAI_API_KEY) through `resolve_secret`. SSL: query param OR config `disable_ssl` (either disables verify); 10s httpx timeout; upstream HTTP errors pass status through, other exceptions → 502.

**Flow:** read force_env → unless set, load+validate draft LLMConfig (fallback default config if load fails) → provider whitelist check → build URL (litellm normalization) → resolve api_key field (vault:// one-shot resolution; failed resolution ⇒ None, plain values pass through) → branch auth_type: auth_header builds custom header with scheme-aware Bearer prefixing; bearer mode uses key directly then env ladder → no credentials at all ⇒ 400 → request with verify=not(ssl_disabled), timeout=10 → sort model ids.
**Invariant:** The same single `api_key` field serves both auth modes (the UI stores one secret); a vault ref that fails resolution must NOT fall through to being sent literally (check `resolved.startswith("vault://")`); raw Authorization values without an explicit scheme get Bearer prepended so frontend-pasted tokens work; log lines carry prefixes/masks only — never full keys. This endpoint has NO direct unit test at HEAD (coverage caveat; source-read verified; sibling resolver behavior pinned in test suites of the secrets plane).

**Probe:** No direct route test at HEAD (coverage caveat). Adjacent pins: `tests/integration/test_llm_config_publish.py` (draft llm section lifecycle :63/:80/:107).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "list_llm_models _PROVIDER_MODELS_URL auth_header_name disable_ssl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: single-key-field dual-mode auth, scheme-aware Bearer prefixing, vault-ref fail-closed handling, /v1 normalization, masked logging. Adapt provider tables. Omit the env fallback if your deployment always has configured keys. Coverage caveat recorded: no direct unit test at HEAD.
