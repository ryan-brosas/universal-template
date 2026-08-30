<!-- capsule-v2 -->
# Env-slot alias presets — how do you detect "provider credentials are already in the environment" without leaking them, and why pipe-separated slots?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does the UI's one-click embedding-provider detection decide a provider is "ready", what may the response safely echo back, and how are placeholder values rejected?

## Slot = one name OR pipe-separated aliases; ready = every required slot has ANY set alias
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_routes.py:134-328` (`get_knowledge_env_presets`, route `GET /knowledge/env-presets`).
**Signature:** `_aliases(spec) -> spec.split("|")`; `_env_set(name) -> bool`; `_slot_set(spec) -> any(_env_set(n) for n in aliases)`; returns `{presets: [...], always_available: [fastembed, ollama]}`.
**Data Shape:** Per preset: `{id, label, default_provider, default_model, ready, env_vars: {name: bool} (ALL aliases incl. unfilled), env_values: {name: value} (NON-SECRET SET ONLY), missing: [canonical first name per unfilled required slot]}`.

### Decisive source
```python
# knowledge_routes.py:158-167
def _env_set(name: str) -> bool:
    v = (_os.environ.get(name) or "").strip()
    if not v:
        return False
    # Reject angle-bracket placeholders ("<your-key>") -- common in .env
    # templates and would falsely flag the slot as ready.
    return not (v.startswith("<") and v.endswith(">"))
```
Secret filtering rides the ONE shared predicate `is_secret_field_name` (imported from manage_routes.helpers and aliased locally; comment :176-178: "One rule across env-presets / GET-redactor / PATCH-preserver — adding a sixth substring updates all three call sites"). `env_values` includes only non-secret vars (URLs, regions, project ids) so the row can render "what was detected"; credential material is never echoed. The watsonx preset demonstrates the alias grammar: required_env `["WATSONX_APIKEY|WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL|WATSONX_API_BASE"]` — slot-level aliases eliminate the old special case AND accept both LiteLLM spellings. Apply semantics: UI sets provider+model only, leaves api_key empty, engine+LiteLLM read the env var at embed-time.

**Flow:** iterate 10 cloud presets → for each slot expand aliases → record per-name booleans + non-secret values → `ready = all(required slots satisfied)` → missing = canonical names for UX → append two local providers as always-available.
**Invariant:** Detection responses must be safe in logged-out/shared contexts: booleans for everything, values only for non-secret fields, placeholders (`<...>`) never count as "set". One secret-name predicate shared by three call sites keeps redaction/detection/preservation consistent.

**Probe:** No direct unit test at HEAD (coverage caveat) — behavior verified by source read; adjacent surface tests live in `tests/unit/test_knowledge_defaults_endpoint.py` (same router family).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "get_knowledge_env_presets PROVIDER_PRESETS required_env is_secret_field_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the slot/alias readiness grammar + placeholder rejection + non-secret-only value echo for any "detect my configured providers" surface. Adapt the preset table to your providers. Omit always_available if locals are handled elsewhere. Coverage caveat recorded: no direct unit test at HEAD.
