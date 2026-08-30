<!-- capsule-v2 -->
# Secret resolution & state-message slots — execution-time credentials + one replaceable context

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how does an LLM use real credentials without ever seeing them, and how does per-step context stay cache-friendly and bounded?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/tools/registry/service.py`: `execute_action` (:331), `_replace_sensitive_data` (:427-516, recursive dict/list replacement + `type(params).model_validate()` round-trip), `_log_sensitive_data_usage` (:421); `browser_use/agent/message_manager/service.py`: `create_state_messages` (:424), `_get_sensitive_data_description` (:391), `_set_message_with_type('state')` filtering (:556); tests pin behavior at `tests/ci/security/test_sensitive_data.py`.
**Signature:** secrets declared as `{domain_glob: {key: value}}`; prompts carry only `<secret>key</secret>` tags; substitution happens INSIDE `execute_action`, after param validation, before handler dispatch.
**Data Shape:** special params (`browser_session`, `page_url`, `page_extraction_llm`, `file_system`, `has_sensitive_data`) injected by the registry, never LLM-visible; state/context messages capped at 60k chars with head+tail truncation (first 100 + last 100).

### Decisive source
```ts
# 1. DOMAIN SCOPING — secrets apply only when current URL matches the glob
#    (and never on new-tab pages); legacy flat {key: value} = everywhere
# 2. TAGGED replacement first, then literal-name fallback for when the LLM
#    passes the bare placeholder name as the whole value
# 3. TOTP: placeholder ending 'bu_2fa_code' -> pyotp.TOTP.now() LIVE code,
#    not the stored secret
# 4. type-preserving round-trip:
dumped = params.model_dump()
replaced = recursively_replace_secrets(dumped)
params = type(params).model_validate(replaced)
# 5. missing placeholders -> collected warning, never fatal; usage logged
# prompt side: _get_sensitive_data_description teaches the <secret> convention;
# stored STATE messages have real values filtered OUT (results leak into history);
# system/context messages skip filtering (they never carry results)
```

**Flow:** user passes real secrets + patterns → MessageManager teaches the model the tag convention → model emits actions containing `<secret>key</secret>` → execute_action validates params, resolves tags by current-URL scope (TOTP placeholders mint fresh codes), re-validates the typed model, injects special params, dispatches → any result text containing real values is filtered before storage in the state message. Per step there is exactly ONE user-visible state message replacing the previous in a fixed slot (cache-prefix friendly, growth-proof); transient extras go to short-lived context messages.
**Invariant:** raw secrets exist only in the executor's scope, scoped by URL pattern; 2FA codes are minted at use-time; replacement preserves param types via dump/validate round-trip; one replaceable state message beats append-only transcripts; mutable-default guard ensures fresh state per manager instance (no cross-run contamination).
**Probe:** `tests/ci/security/test_sensitive_data.py` (domain scoping; TOTP path; tag-forgiving fallback; type round-trip); message-manager tests pin `keep_last_items=6`, `summary_max_chars=6000`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_replace_sensitive_data execute_action create_state_messages sensitive_data TOTP bu_2fa_code", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt URL-scoped execution-time secret resolution with TOTP minting and typed round-trips, plus the single-replaceable-state-message layout. Adapt scope syntax to host.
