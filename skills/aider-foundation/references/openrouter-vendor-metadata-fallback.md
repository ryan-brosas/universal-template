<!-- capsule-v2 -->
# OpenRouter vendor metadata fallback — how do you resolve third-party model metadata without forcing a heavy SDK import or breaking offline?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you serve `openrouter/<vendor>/<model>:variant` lookups from a cached vendor feed, and what should each failure class do to the cache?

## Variant-stripped lookup over an mtime-TTL feed with poison-on-exception asymmetry
**Path/Symbol:** `aider/openrouter.py` whole (128 L): `_cost_per_token` (:19-26), `OpenRouterModelManager` (:29-128), `set_verify_ssl` (:43-45), `get_model_info` (:47-83), `_strip_prefix` (:88-89), `_ensure_content` (:91-94), `_load_cache` (:96-112), `_update_cache` (:114-128). Consumer: `models.ModelInfoManager` instantiates it as the `openrouter/` fallback and re-applies `set_verify_ssl` AFTER construction because verify_ssl can flip post-init.
**Signature:** `get_model_info(model: str) -> Dict`; `_load_cache() -> None`; `_update_cache() -> None`.
**Data Shape:** cache file `~/.aider/caches/openrouter_models.json`, TTL 24 h by mtime; content = `{"data": [{"id", "pricing": {"prompt","completion"}, "context_length", "top_provider": {"context_length"}}]}`; return dict maps context_len to ALL THREE of max_input_tokens/max_tokens/max_output_tokens plus per-token costs and hardcoded `"litellm_provider": "openrouter"`.

### Decisive source
```python
route = self._strip_prefix(model)
candidates = {route}
if ":" in route:
    candidates.add(route.split(":", 1)[0])          # :61-63 model:free resolves the BASE record
record = next((item for item in self.content["data"] if item.get("id") in candidates), None)
...
context_len = (record.get("top_provider", {}).get("context_length")
               or record.get("context_length") or None)   # :69-73 ladder copied to all three max_*
```

```python
if response.status_code == 200:
    self.content = response.json()
    try: self.cache_file.write_text(json.dumps(self.content, indent=2))
    except OSError: pass                        # :121-122 write-through best-effort
except Exception as ex:
    print(f"Failed to fetch OpenRouter model list: {ex}")
    try: self.cache_file.write_text("{}")       # :126 POISON — parses falsy, refetches per lookup
    except OSError: pass
```

**Flow:** lookup first ensures content: `_load_cache` is a one-shot latch (`_cache_loaded`) that reads the JSON only when mtime age < 24 h; `JSONDecodeError` treats the file as absent; unwritable dirs are ignored. Empty content triggers `_update_cache`: 10 s timeout honoring `verify_ssl`. Matching strips `openrouter/`, then accepts either the exact id or the id with any `:variant` suffix split off. Pricing strings parse via `_cost_per_token`: `"0"`→0.0, but `""`/None/unparseable→None (free models are 0.0; unknowns stay unknown). **Poison asymmetry:** HTTP non-200 leaves `self.content` unset WITHOUT touching the file; only the EXCEPTION path prints and overwrites the cache with `"{}"` — which parses falsy so every later instance refetches until success or TTL expiry, while within the SAME instance every lookup retries the network while content stays None.
**Invariant:** litellm is never imported for this path; offline sessions degrade to `{}` metadata instead of raising; a corrupt or failed fetch can never wedge the manager because falsy content always re-attempts. Untested upstream: the exception-path poison branch has no direct test (the suite drives cache-hit + delegation paths); treat the poison semantics as source-pinned.
**Probe:** `.venv/bin/python -m pytest tests/basic/test_openrouter.py -q` → **2 passed** (executed this run; monkeypatched requests.get + Path.home drive both the cache-hit path and ModelInfoManager delegation :47-73).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "OpenRouterModelManager", limit: 10 });
// total:8/8 nodes — Class 29-128, get_model_info 47-83, _load_cache 96-112, _update_cache 114-128, set_verify_ssl 43-45,
// _strip_prefix 88-89, _ensure_content 91-94, __init__ 33-38
```

## Verdict
Adopt the shape: prefix-strip → variant-tolerant candidate set → cached-feed scan → context ladder into a provider-neutral dict, behind an mtime-TTL latch that never imports the heavy SDK. Adapt TTL, endpoint, and field mapping to your vendor. Keep the poison asymmetry deliberate: decide explicitly whether transport errors should poison-and-retry (aider's choice) or back off quietly — do not inherit it by accident.
