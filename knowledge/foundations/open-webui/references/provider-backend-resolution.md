<!-- capsule-v2 -->
# Provider backend resolution — How do you route one logical model across N backends with per-backend keys and config?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When a model is served by several provider backends (or a caller pins one), how is the URL, API key, and per-connection config resolved — and what does a non-admin caller get to choose?

## Backend selection + config fallback seam
**Path/Symbol:** `backend/open_webui/routers/ollama.py:get_ollama_url` (1068-1083), `validate_ollama_backend_idx` (1055-1065), `resolve_api_config` (369-371), `get_api_key` (199-202); OpenAI twin `backend/open_webui/routers/openai.py:get_openai_connection` (300-305).
**Signature:** `async def get_ollama_url(request, model: str, url_idx: int | None = None, user=None) -> tuple[str, int]`; `async def validate_ollama_backend_idx(request, model, url_idx, user) -> None`; `def resolve_api_config(api_configs: dict, idx: int, url: str) -> dict`; `def get_api_key(idx, url, configs)`; `async def get_openai_connection(idx: int) -> tuple[str, str, dict]`.
**Data Shape:** `ollama.base_urls`: list[str]; `models[model]['urls']`: list[int] indices; api_configs keyed by str(idx) with legacy base-url key; parallel arrays for openai urls/keys.

### Decisive source
```python
    if url_idx is None:
        models = request.app.state.OLLAMA_MODELS
        if not models or model not in models:
            await get_all_models.cache.clear()
            await get_all_models(request, user=user)
            models = request.app.state.OLLAMA_MODELS
        if model not in models:
            raise HTTPException(400, detail=ERROR_MESSAGES.MODEL_NOT_FOUND(model))
        url_idx = random.choice(models[model].get('urls', []))
    url = (await Config.get('ollama.base_urls', []))[url_idx]
    return url, url_idx
```

```python
def get_api_key(idx, url, configs):
    parsed_url = urlparse(url)
    base_url = f'{parsed_url.scheme}://{parsed_url.netloc}'
    return configs.get(str(idx), configs.get(base_url, {})).get('key', None)  # Legacy support
```

**Flow:** caller-supplied url_idx → validated against the model's backend allow-list (`validate_ollama_backend_idx`, 403 ACCESS_PROHIBITED on mismatch; admin/BYPASS exempt) → else random choice over the model's backend list as load balancing → cache miss triggers clear-and-refetch of all models BEFORE declaring MODEL_NOT_FOUND → URL from base_urls[url_idx]; key/config resolved by str(idx) first, legacy base-url key second.
**Invariant:** a non-admin caller can never steer a request to a backend the model isn't served from; resolution must degrade to legacy config layouts (`str(idx)` → base-url key) without a migration; cache refetch happens before any NOT_FOUND so a freshly-added backend model is immediately routable.
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "url_idx = random.choice(models\[model\].get('urls', \[\]))" backend/open_webui/routers/ollama.py` → line 1081; `grep -n "configs.get(str(idx), configs.get(base_url, {}))" backend/open_webui/routers/ollama.py` → line 202.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_ollama_url validate backend idx resolve_api_config get_openai_connection", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves all five symbols at their cited ranges.

## Verdict
Adopt: allow-list validation of pinned backends, random-choice balancing over per-model backend lists, refetch-before-not-found, two-key config fallback. Adapt: storage of base_urls/keys to host config plane (open-webui reads dotted Config keys). Omit: prefix_id namespacing interplay (covered in ollama-model-aggregation). Caveat: zero direct tests upstream; `request.state.bypass_filter/bypass_system_prompt` flags consumed here are internal-only by design (comment 1098-1106 in both routers).
