<!-- capsule-v2 -->
# JSON-body 400 contract + vault secret-ref preservation — how do you turn malformed input into a client error and keep secret POINTERS from being wiped by redaction?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f` (#689/#695); Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** `await request.json()` on an absent/malformed body escapes as a 500 with traceback, and redacting "secret-named fields" silently destroys stored `vault://…` pointers — what are the correct contracts?

## _json_body helper + is_secret_ref allow-list
**Path/Symbol:** `src/cuga/backend/knowledge/routes.py:63-96` (`_json_body(request, *, allow_empty=False)`, applied at :301/:349/:701/:799/:904/:928 replacing raw `request.json()`), upload temp-file cleanup :623-632; `server/manage_routes/helpers.py:85-107` (`is_secret_ref`, `redact_secrets_in_config` skip-ref branch); merge-without-wipe `server/manage_routes/draft_routes.py:146-172` (`patch_draft_llm`: lock → load → drop EMPTY secret fields → `{**existing_llm, **llm}` merge).
**Signature:** `async _json_body(request, *, allow_empty=False) -> dict`; `is_secret_ref(value) -> bool` (vault:// | db:// | aws:// | env://).

### Decisive source
```python
# routes.py:74-88 — only DECODING failures are the client's fault
    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        # Only decoding failures become a 400. Anything else (a disconnect
        # mid-read, for one) is not the client sending bad JSON and must
        # propagate rather than be reported as a malformed request.
        raise HTTPException(status_code=400, detail=detail)
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail=detail)
```
```python
# helpers.py:97-107 — pointers survive; plaintext does not
def redact_secrets_in_config(config):
    """In-place: replace secret-named non-empty string fields with ''.
    Secret refs (vault://, db://, aws://, env://) are kept so Manage can
    hydrate 'Use saved secret'."""
        if is_secret_field_name(k) and isinstance(v, str) and v and not is_secret_ref(v):
            node[k] = ""
```

**Flow:** `_json_body` reads raw bytes first — empty body yields 400 (or `{}` when `allow_empty`, for endpoints where every field is optional; whitespace-only still parses-and-400s because that's malformed, not absent). The detail string reuses the one `patch_session_settings` already shipped ("request body must be a JSON object") so no client-matched message moves — only status codes change from 500→400. On the manage side, GET /config keeps refs visible to the UI while blanking plaintext; PATCH merges field-wise under the per-agent draft lock and drops only EMPTY incoming secret fields, so a UI autosave that sends `api_key:""` can never wipe a stored `vault://` pointer.

**Invariant:** (1) 400 vs 500 by FAULT DOMAIN: bad client payload = 4xx, server-side transport/parse-layer surprises propagate. (2) A secret FIELD NAME is not a secret VALUE — redaction must distinguish pointers (scheme-prefixed) from material, or every GET-after-save destroys the credential reference. (3) Empty-string secret in a PATCH means "unchanged", not "clear" (clearing goes through dedicated unset flows). (4) Upload handlers unlink their temp file on EVERY failure path including unexpected exceptions.

**Probe:** direct tests `tests/unit/test_knowledge_json_body.py` (absent/malformed/non-object/allow-empty matrix — 140 lines); `tests/unit/test_manage_llm_secret_ref.py::test_*` (:1-78 ref preservation through PATCH+GET round-trip); `tests/unit/test_manage_secret_redaction.py` (+42 lines covering the is_secret_ref branches); integration `tests/integration/test_vault_llm_secret_hydration.py` (138 lines, dropdown hydration).

## Get live surrounding code
**Retrieve:**
```ts
mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_json_body is_secret_ref redact_secrets_in_config patch_draft_llm", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** ADOPT both contracts in any API surface backed by stored credentials: parse request bodies through one helper that maps fault domain to status class, and make secret redaction pointer-aware before it ever touches config round-trips.
