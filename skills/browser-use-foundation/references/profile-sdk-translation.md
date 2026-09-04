<!-- capsule-v2 -->
# Profile-to-SDK translation — how do you forward a Python-side browser config to a foreign core without leaking secrets or losing defaults?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does the wrapper translate `BrowserProfile`/`BrowserSession` settings into (a) an env dict for the Rust child and (b) a JSON payload, when neither side shares types?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — extraction helpers `_extract_profile_domains` (:1123), `_extract_wait_timing_settings` (:947), `_managed_browser_launch_args` (:810), `_extract_browser_viewport` (:1025), `_sensitive_data_context` (:1140), `_warn_sensitive_data_domain_constraints` (:1169), `_llm_env_overrides` (:1218); consumers `Agent._run_env` :6723 and `_sdk_browser_payload` / `_sdk_run_params` :6531.
**Signature:** `_run_env(self) -> dict[str,str]`; `_sdk_run_params(*, max_steps, task, followups) -> dict`; `_extract_profile_domains(session, profile, attr) -> list[str]`.
**Data Shape:** every extractor walks the SAME precedence chain `(session.browser_profile, explicit_profile, session)` taking the first typed value; env keys are the flat `BU_*`/`BROWSER_USE_TERMINAL_*` family (`BU_BROWSER_ALLOWED_DOMAINS`, `BU_BROWSER_VIEWPORT`, `BU_MANAGED_BROWSER_ARGS`, …); payload uses nested camelCase (`deviceScaleFactor`, `screenWidth`).

### Decisive source
```python
# first-typed-value-wins precedence over the triple view:
for profile in (session_profile, browser_profile, browser_session):
    value = getattr(profile, attr, None)
    if isinstance(value, bool): return value
# sets are sorted before serialization so env JSON is deterministic:
if isinstance(raw_args, set): raw_args = sorted(raw_args)
# viewport derivation with no_viewport override:
if no_viewport is True:  return no_viewport, None
if viewport_size is None and no_viewport is False:
    viewport_size = screen_size          # headful default = screen
viewport = {'width':w,'height':h,'deviceScaleFactor': 1 if dsf is None else dsf}
# sensitive data crosses as NAMES ONLY — values stay in Python:
return {'global_placeholders': sorted(global_placeholders),
        'domain_placeholders': {domain: [names...]}}
# LLM creds injected per provider into vendor-specific env names:
overrides['LLM_BROWSER_OPENAI_API_KEY'] = api_key   # openai | anthropic | openrouter | deepseek | browser-use
```

**Flow:** at construction all extractors snapshot profile state once into attributes; `_run_env()` copies os.environ then layers: provider-keyed LLM overrides → cost flags (`BU_USE_CALCULATE_COST`, usage-inclusion for openrouter/deepseek) → browser mode → wait timings (seconds→ms) → domain allow/block JSON → downloads/viewport/storage-state → managed-browser args/profile-dir/executable-path ONLY when mode ∈ managed set (`_is_managed_browser_mode` :1106 normalizes `_`→`-`); `_sdk_browser_payload()` mirrors the same fields as omit-when-None JSON via its `put()` helper.
**Invariant:** secret VALUES never cross to the child — placeholders by name plus `<secret>` instructions in the task text; sets are sorted everywhere so identical configs produce byte-identical env; managed-only fields are gated by the same normalized-mode predicate on both sides; missing values are omitted, never sent as null/empty.
**Probe:** `tests/ci/test_beta_agent.py:3891` `test_beta_agent_translates_browser_profile_downloads`, `:3951` storage_state, `:4038` env, `:4078` domain constraints, `:4100` `test_beta_agent_adds_sensitive_data_placeholders_without_values`, `:4123` warns about uncovered domains.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_run_env _sdk_browser_payload _extract_wait_timing_settings BU_BROWSER_ALLOWED_DOMAINS", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the first-typed-value precedence walk + names-only secret handoff + deterministic-set sorting + managed-mode gating for any dual-process config bridge; adapt env key vocabulary and provider list; omit cloud-specific fields (`profile_id`, `proxy_country_code`) unless your core supports them.
