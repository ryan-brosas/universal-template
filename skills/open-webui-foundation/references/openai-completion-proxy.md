<!-- capsule-v2 -->
# OpenAI completion proxy — How do you normalize one OpenAI-ish payload across vanilla, Azure, and Responses dialects in a single proxy entry point?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** What is the ordered payload-normalization and transport-selection ladder that lets one endpoint serve api.openai.com, Azure deployments (v1 and legacy), Responses-API backends, and arbitrary OpenAI-compatible servers?

## Completion proxy seam
**Path/Symbol:** `backend/open_webui/routers/openai.py:generate_chat_completion` (1182-1435); helpers `openai_reasoning_model_handler` (135-153), `_clean_proxy_headers` (85-87).
**Signature:** `async def generate_chat_completion(request: Request, form_data: dict, user=Depends(get_verified_user))` → JSON dict | StreamingResponse | JSONResponse(error) | PlainTextResponse(error).
**Data Shape:** input dict with optional `metadata` popped first; routing key = `model['urlIdx']` from app.state cache; `api_config` carries `azure`, `provider`, `auth_type`, `api_type`, `api_version`, `prefix_id`, `headers`.

### Decisive source
```python
    if api_config.get('azure') or api_config.get('provider') == 'azure':
        auth_type = api_config.get('auth_type', 'bearer')
        if auth_type not in ('azure_ad', 'microsoft_entra_id'):
            headers['api-key'] = key
        is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))
        if is_azure_v1:
            ...  # model stays in payload; no deployment rewrite
        else:
            request_url, payload = convert_to_azure_payload(url, payload, api_version)
            headers['api-version'] = api_version
    else:
        ...
    if not is_responses and 'messages' in payload:
        for message in payload['messages']:
            if message.get('role') == 'tool' and isinstance(message.get('content'), list):
                message['content'] = ''.join(
                    part.get('text', '') for part in message['content'] if part.get('type') in ('input_text', 'text'))
    if not is_streaming_request:
        payload.pop('stream_options', None)
...
        if 'text/event-stream' in r.headers.get('Content-Type', ''):
            if r.status >= 400:
                error_body = await r.text()   # never stream an error back
                return JSONResponse(status_code=r.status, content=error_json)
```

**Flow:** enable-flag → bypass flags from request.state only → base_model_id override + params/system application + access check → model→urlIdx via cache (refetch-on-miss) → prefix strip → pipeline models get a full `user` object → reasoning-model handler (max_tokens→max_completion_tokens; system→developer role, o1-mini/o1-preview keep user) → non-api.openai.com compat shim restores max_tokens from max_completion_tokens; both present ⇒ drop max_tokens → logit_bias JSON conversion → azure-v1-vs-deployment URL/payload ladder; `api_type=='responses'` converts payload AND result both directions → transport through shared pool with stream-aware timeout → SSE+4xx/5xx gate reads the body and returns a proper error response.
**Invariant:** bypass flags can never arrive from query params (request.state read-only contract); long LLM calls never hold a DB session (`Depends(get_async_session)` deliberately omitted — comment 1190-93); an upstream error with SSE content-type must surface as JSON/loggable text, never as a fake event stream; non-streaming requests never carry stream_options.
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "is_azure_v1 = bool(re.search(r'/openai/v1(?:/|$)', url))" backend/open_webui/routers/openai.py` → line 1294; `grep -n "payload.pop('stream_options', None)" backend/open_webui/routers/openai.py` → line 1330.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "generate_chat_completion openai proxy azure responses convert_to_responses_payload", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves `routers.openai.generate_chat_completion` 1182-1435 (fan-in hotspot `responses` 1565-1671 sits behind it).

## Verdict
Adopt: dialect-dispatch ladder order (azure check before generic), v1-vs-deployment regex fork, both-ways Responses conversion boundary, tool-message image stripping for Chat Completions, SSE-error-as-JSON gate. Adapt: converter internals — both converters live IN THIS FILE, not a utils payload module (`def convert_to_azure_payload` openai.py:950-977, `def convert_to_responses_payload` openai.py:1005-1144); read them whole before porting. Omit: pipeline `user` object injection unless porting open-webui pipelines. Caveats: zero direct tests upstream; the azure-v1 regex fork is duplicated across sibling endpoints (`is_azure_v1` also at :821 embeddings, :1478, :1606, :1723 proxy/responses twins) — keep forks in sync when porting; streaming uses `stream_wrapper(r, content_handler=stream_chunks_handler)` (:1394), not passthrough mode.
