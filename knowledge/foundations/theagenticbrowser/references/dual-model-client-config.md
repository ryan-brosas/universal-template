<!-- capsule-v2 -->
# Dual config + env client factory — how do two different models (text vs vision) share one provider without leaking credentials into code?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you wire multiple OpenAI-compatible model roles so each agent gets its configured endpoint, with loud startup failures and no hardcoded keys?

## Prefixed env families, fail-fast get_env_var, normalized base URL
**Path/Symbol:** `core/utils/openai_client.py`:`OpenAIConfig` (`:21-60`), `get_env_var` (`:14-19`), `create_client_with_retry` (`:82-97`), `get_client`/`get_ss_client` (`:99-107`), `validate_models` (`:62-80`).
**Signature:** `OpenAIConfig.get_text_config() -> Dict`; `get_ss_config() -> Dict`; `def create_client_with_retry(client_class, config: dict)`; `async def validate_models(client: AsyncOpenAI) -> bool`.
**Data Shape:** Two disjoint env families read at EVERY call (no caching): `AGENTIC_BROWSER_TEXT_{MODEL,API_KEY,BASE_URL}` and `AGENTIC_BROWSER_SS_{MODEL,API_KEY,BASE_URL}`; both configs carry `max_retries=3, timeout=30.0`. `.env.example` documents all six plus `AGENTIC_BROWSER_SS_ENABLED`, `GOOGLE_API_KEY`, `GOOGLE_CX`, `BROWSER_STORAGE_DIR`, `STEEL_DEV_API_KEY`, `LOG_LEVEL`.

### Decisive source
```python
@staticmethod
def validate_model(model: str) -> bool:
    """Validate if the model name matches known patterns"""
    return True          # placeholder: accept anything, error surfaces at the API

def create_client_with_retry(client_class, config: dict):
    base_url = config["base_url"].rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return client_class(api_key=config["api_key"], base_url=base_url,
                        max_retries=config["max_retries"], timeout=config["timeout"])
```
`get_ss_client()` deliberately returns the SYNC OpenAI class (vision analysis runs inline in ImageAnalyzer), while `get_client()` returns AsyncOpenAI for all three pydantic-ai agents. Optional `validate_models()` lists `/v1/models` and raises ModelValidationError when either configured id is absent — a startup smoke test wired via `initialize_and_validate()`.
**Flow:** import-time module singletons in agents/final_response call `get_client()` → per-role config dict → client with retry/timeout → same model name reused by pydantic-ai `OpenAIModel(model_name=os.getenv(...))`.
**Invariant:** The sync/async split is load-bearing (ImageAnalyzer.analyze_images is a plain def inside async orchestration). Missing env vars raise ValueError naming the variable — never a silent default key or URL. The no-op validator means "model exists" is enforced only if you opt into the /models round-trip.
**Probe:** No tests (coverage caveat). Graph pin: 11 EnvVar nodes in the graph index (`index_status` node_labels) map 1:1 to these names; `trace_path --function-name get_client --direction inbound` fans out to all four consumer modules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "openai client config text ss model", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt prefixed per-role env families with fail-fast reads and transport-level retry defaults. Adapt the family prefix and add real model validation for production. Omit the /models check when your gateway doesn't implement it — but keep missing-var errors loud.
