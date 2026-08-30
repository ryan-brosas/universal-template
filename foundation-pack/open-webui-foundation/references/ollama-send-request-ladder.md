<!-- capsule-v2 -->
# Ollama send-request ladder — How do you proxy upstream errors without masking them while keeping streams alive?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When a proxied provider call fails, what exactly reaches the client, what reaches telemetry, and who releases the connection?

## Proxy request/error ladder seam
**Path/Symbol:** `backend/open_webui/routers/ollama.py:send_request` (96-196).
**Signature:** `async def send_request(url: str, method: str = 'POST', *, payload=None, key=None, user=None, stream=False, passthrough=False, content_type=None, metadata=None, api_config=None, request=None)`.
**Data Shape:** returns parsed JSON dict, `None` on unparseable 2xx body, or a `StreamingResponse` (headers cleaned; Content-Type forced e.g. `application/x-ndjson`); raises `HTTPException` carrying upstream status + upstream `'error'` detail when available.

### Decisive source
```python
        # Custom per-connection headers last so admin-set headers take precedence.
        if api_config and api_config.get('headers'):
            headers.update(await get_custom_headers(api_config['headers'], user, metadata, request=request))
...
        if not r.ok:
            try:
                res = await r.json(loads=JSONCodec.loads)
                await publish_model_provider_request_failed(..., upstream_error=res)
                if 'error' in res:
                    raise HTTPException(status_code=r.status, detail=res['error'])
            except HTTPException:
                raise
            except Exception as e:
                log.error(f'Failed to parse error response: {e}')
                await publish_model_provider_request_failed(...)   # no upstream_error
            raise HTTPException(
                status_code=r.status,
                detail=ERROR_MESSAGES.SERVER_CONNECTION_ERROR,
            )
...
    finally:
        if not streaming:
            await cleanup_response(r)
```

**Flow:** build headers in fixed precedence (Bearer key → optional user-info forward + chat-id session header → custom per-connection LAST so admin values win) → issue via shared pool with stream-aware timeout → non-ok: extract JSON error, publish failure event, re-raise upstream detail preserving status; unparseable error body still publishes then raises generic SERVER_CONNECTION_ERROR with upstream status → ok+stream: hand response ownership to StreamingResponse over `stream_wrapper` and skip finally-cleanup → ok+unary: JSON decode, decode failure returns None (never raises).
**Invariant:** upstream status codes are never replaced by 500 when the response arrived; the upstream `'error'` string is surfaced verbatim before any generic message; telemetry (`publish_model_provider_request_failed`) fires on BOTH parse-success and parse-failure arms; cleanup ownership flips exactly once via the `streaming` flag — the shared session is never released.
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "Custom per-connection headers last" backend/open_webui/routers/ollama.py` → line 126; `grep -n "passthrough must stay False for /api/chat" backend/open_webui/routers/ollama.py` → line 104.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "send_request ollama proxy passthrough publish_model_provider_request_failed", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves `routers.ollama.send_request` 96-196 as top hit; live trace_path inbound reports callers_total=41 (ollama router endpoints, tasks.py background generators, middleware handlers, utils.chat dispatcher).

## Verdict
Adopt: header-precedence ladder, error-transparency ladder (upstream detail > generic), failure-event-on-both-arms, streaming ownership flip. Adapt: event publisher and ERROR_MESSAGES catalog to host. Omit: Ollama-specific NDJSON content-type forcing unless proxying Ollama. Caveat: `passthrough` must stay False for `/api/chat` because downstream middleware parses the stream line-by-line — documented only in a parameter comment at :104.
