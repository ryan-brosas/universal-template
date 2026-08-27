<!-- capsule-v2 -->
# Model-info cache ladder — sourcing model metadata without forcing the heavy import or the network

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** When local files, a disk cache, litellm's price DB, and vendor pages can all answer "what are this model's limits/costs", what precedence do you use — and what happens offline or with a corrupt cache?

## Local json5 overrides -> 24h disk cache -> litellm (only if needed) -> vendor fallbacks
**Path/Symbol:** `aider/models.py`: `ModelInfoManager` (:161-323), module singleton `model_info_manager` (:326); `register_litellm_models(model_fnames)` (:1112-1133) feeding `local_model_metadata`; `register_models(model_settings_fnames)` (:1085-1109) for settings.
**Signature:** `get_model_info(model) -> dict`; `_load_cache()`; `_update_cache()`; `get_model_from_cached_json_db(model) -> dict`.
**Data Shape:** `CACHE_TTL = 24h` by file mtime; cache at `~/.aider/caches/model_prices_and_context_window.json`; `_cache_loaded` once-guard; `MODEL_INFO_URL` points at litellm's GitHub price DB.

### Decisive source
```python
def _load_cache(self):
    if self._cache_loaded:
        return
    try:
        ...
        if self.cache_file.exists():
            cache_age = time.time() - self.cache_file.stat().st_mtime
            if cache_age < self.CACHE_TTL:
                try:
                    self.content = json.loads(self.cache_file.read_text())
                except json.JSONDecodeError:
                    self.content = None      # corrupt cache == absent
    except OSError:
        pass
    self._cache_loaded = True            # negative attempts are cached too

def _update_cache(self):
    try:
        response = requests.get(self.MODEL_INFO_URL, timeout=5, verify=self.verify_ssl)
        if response.status_code == 200:
            self.content = response.json()
            self.cache_file.write_text(json.dumps(self.content, indent=4))
    except Exception as ex:
        print(str(ex))
        self.cache_file.write_text("{}")   # failure still writes a parseable tombstone

def get_model_info(self, model):
    cached_info = self.get_model_from_cached_json_db(model)
    if litellm._lazy_module or not cached_info:      # never force the lazy import
        litellm_info = ... litellm.get_model_info(model) ...
    if not cached_info and model.startswith("openrouter/"):
        openrouter_info = self.openrouter_manager.get_model_info(model)
        if openrouter_info: return openrouter_info
        openrouter_info = self.fetch_openrouter_model_info(model)   # HTML-scrape fallback
        if openrouter_info: return openrouter_info
    return cached_info
```

**Flow:** user json5 model files merge into `local_model_metadata` FIRST (`model_info_manager.local_model_metadata.update(model_def)`, :1127 — import-deferred "faster path") -> two-piece "provider/name" fallback matches name with `litellm_provider` equality (:241-245) -> disk cache when <24h old; corrupted JSON treated as missing -> live fetch (5s timeout honoring verify_ssl) write-through on success -> on ANY failure the cache file becomes "{}", which parses but stays falsy so every subsequent lookup retries the network until success or TTL expiry -> litellm consulted only when already imported OR local data was empty -> `openrouter/` prefix falls back to the cached OpenRouter DB, then legacy page scraping.
**Invariant:** the heavy litellm import is NEVER forced when local data answers; settings registration replaces per-name via in-place splice `MODEL_SETTINGS[:] = [ms for ms in MODEL_SETTINGS if ms.name != name]` (:1102) preserving list identity; every failure path leaves a readable state (None content or "{}" file), never an exception.
**Probe:** `tests/basic/test_model_info_manager.py` — `test_lazy_loading_cache` (:43), `test_update_cache_respects_verify_ssl` (:26), `test_verify_ssl_setting_before_cache_loading` (:64). Executed GREEN this run (repo `.venv`, suite incl. this file: 30 passed, 1 skipped). Anchors: `grep -nF 'CACHE_TTL = 60 * 60 * 24' aider/models.py` -> :166; `grep -nF 'litellm._lazy_module or not cached_info' aider/models.py` -> :253; `grep -nF 'write_text("{}")' aider/models.py` -> :219.
**Coverage caveat:** `fetch_openrouter_model_info` scraping branch has no direct test — treat its regex pricing as best-effort source-pinned behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "ModelInfoManager", limit: 8 });
// resolves __init__/_load_cache/_update_cache/set_verify_ssl/get_model_info line-exact
```

## Verdict
Adopt the precedence ladder (local override > TTL disk cache > provider SDK > vendor scrape) with the lazy-import guard and the parseable-failure tombstone. Adapt URLs, TTL, and scrape regexes to the host; omit Aider's singleton wiring if your DI story differs. Porters who let cache-load failures throw will brick offline startups.
