<!-- capsule-v2 -->
# Ollama model aggregation — How do you aggregate model lists from N backends when some are down or disabled?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How do you fan out a census call across N provider backends so that failures and disabled entries never corrupt per-index post-processing?

## Fan-out aggregation seam
**Path/Symbol:** `backend/open_webui/routers/ollama.py:get_all_models` (386-451); helper `send_get_request` (68-93).
**Signature:** `async def get_all_models(request: Request, user: UserModel | None = None) -> dict` (`{'models': [...]}`; caches into `request.app.state.OLLAMA_MODELS`).
**Data Shape:** per-backend response = Ollama `/api/tags` JSON or None; per-connection api_config keys: `enable`, `key`, `prefix_id`, `tags`, `model_ids`, `connection_type`.

### Decisive source
```python
    for idx, url in enumerate(base_urls):
        api_config = resolve_api_config(api_configs, idx, url)
        if not api_config:
            tasks.append(send_get_request(f'{url}/api/tags', user=user))
        elif api_config.get('enable', True):
            tasks.append(send_get_request(f'{url}/api/tags', api_config.get('key'), user=user))
        else:
            tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))

    responses = await asyncio.gather(*tasks)
...
    for idx, response in enumerate(responses):
        if not response:
            failed_idxs.add(idx)
            continue
...
        for m in response.get('models', []):
            if prefix_id:
                m['model'] = f'{prefix_id}.{m["model"]}'
```

```python
    """Issue a GET request to an Ollama backend and return JSON, or *None* on failure."""
     ...
    except Exception as exc:
        log.error(f'Connection error: {exc}')
        return None
```

**Flow:** build one task PER backend index — disabled backends contribute a completed-no-op future rather than being omitted, so `responses[i]` always corresponds to `base_urls[i]` → gather (never raises; each GET returns None on any failure) → per-index post-process: model_ids allow-list filter, prefix_id namespacing of model ids, forced tags, connection_type stamping; None results recorded into failed_idxs → merge all model lists → annotate loaded-model expiry timestamps (best-effort, skip failed backends) → publish cache dict.
**Invariant:** index alignment between base_urls and responses is preserved by construction (no-op futures for disabled, None for failed) — post-processing may trust position; one dead backend must never fail the whole census; prefixed model ids are the cache key so identically-named models from different backends coexist.
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "tasks.append(asyncio.ensure_future(asyncio.sleep(0, None)))" backend/open_webui/routers/ollama.py` → line 406; `grep -n "m\['model'\] = f'{prefix_id}.{m\[\"model\"\]}'" backend/open_webui/routers/ollama.py` → line 431.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "get_all_models aggregate ollama tags merge_models_lists failed_idxs", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves `routers.ollama.get_all_models` 386-451.

## Verdict
Adopt: index-aligned fan-out with no-op futures, None-on-failure census requests, per-connection prefix/tags/filter stamping. Adapt: cache destination to host app-state convention. Omit: expires_at annotation unless porting Ollama loaded-model state. Caveats: zero direct tests upstream; the no-op-future alignment trick is load-bearing but only visible when reading both get_all_models and send_get_request together; the SAME idiom repeats in the /api/ps aggregator `get_ollama_loaded_models` (no-op futures for skip_idxs/disabled at :513/:522, prefix_id rename at :533) — port both or neither, they share the index contract via failed_idxs.
