<!-- capsule-v2 -->
# Log Secret Scrubber — redact credentials at the handler, not at every call site

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you guarantee a careless `logger.info("%s", body)` can't leak API keys, and how does the scrubber know which replacement style to use?

## Pattern list with group-count-keyed replacement; filter touches msg AND args
**Path/Symbol:** `packages/python/awaithumans/server/core/logging_config.py` — `request_id_var` (:30), `_LOG_SCRUB_PATTERNS` (:40-55), `scrub_text` (:58-69), `_ScrubFilter.filter` (:81-94), `AwaitHumansFormatter.format` (:100-109), `setup_logging` (:112-134).
**Signature:** `scrub_text(value: str) -> str`; `_ScrubFilter` installed via `handler.addFilter(...)` on the ROOT logger (handlers cleared first).
**Data Shape:** patterns: `sk-…{8,}` (OpenAI/Anthropic-style), scoped `sk_…` variants, `Bearer <tok>`, Google `AIza…{35,}`, keyed `password=…`/JSON forms, header lines `x-admin-token:`/`x-slack-signature:`.

### Decisive source
```python
for pattern in _LOG_SCRUB_PATTERNS:
    # Two flavours: simple replacement (group 0) vs keyed replacement
    # (preserve the field name, redact only the value). Distinguished by groups.
    if pattern.groups >= 2:
        value = pattern.sub(r"\1[REDACTED]", value)
    else:
        value = pattern.sub("[REDACTED]", value)
```
The filter scrubs `record.msg` AND each str arg BEFORE formatting — `%s`-style logging of credential objects is caught pre-interpolation. Docstring: belt-and-braces with the verifier-side scrubber ("both must exist because vendor errors aren't the only source").

**Flow:** setup_logging → clear root handlers → add stdout handler with formatter + scrub filter → silence sqlalchemy.engine/uvicorn.access/httpx/httpcore to WARNING → confirmation log. Request correlation rides `request_id_var` set by RequestIDMiddleware; formatter emits ` request_id=<id>` only when non-empty.
**Invariant:** scrubbing happens for EVERY record regardless of logger (root-handler placement); idempotent (`test_scrubber_idempotent`:56); no-match passes through untouched.
**Probe:** `packages/python/tests/core/test_logging_scrub.py` (`test_scrubs_openai_anthropic_style_key`:13, `test_scrubs_bearer_token`:25, `test_scrubs_password_in_json`:38, `test_scrubs_x_admin_token_header_line`:50, `test_no_match_passes_through`:64) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "scrub_text _ScrubFilter _LOG_SCRUB_PATTERNS request_id", limit: 4 });
```
Live rank-1..3 line-exact (:58-69, :81-94, class :72-94).

## Verdict
Adopt the handler-level filter + group-count dispatch + args-scrubbing trio; adapt patterns to your secret formats; omit the request-id correlation only if your platform already injects trace ids into logs.
