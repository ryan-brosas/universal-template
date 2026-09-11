<!-- capsule-v2 -->
# Boot URL/CORS gatekeepers — how does a self-hosted server refuse credential-leaking CORS and malformed PUBLIC_URL configs before serving a single request?

**Source:** awaithumans (Apache-2.0) `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** Where do I enforce "the operator typed a CORS/public-URL value that would leak session cookies or stack paths onto every constructed URL", and what shapes survive?

## Boot-time validator pair
**Path/Symbol:** `packages/python/awaithumans/server/app.py:_validate_cors_origins` (:483–524), `_validate_public_url` (:527–570); consumed at :356 and :388 during app creation; middleware wiring at :429–432.
**Signature:** `_validate_cors_origins(origins: list[str]) -> None` / `_validate_public_url(url: str) -> None` — both raise `RuntimeError` (fail boot).
**Data Shape:** `origins = settings.cors_origin_list` (split of `AWAITHUMANS_CORS_ORIGINS`, config.py :219–223); `url = settings.PUBLIC_URL`.

### Decisive source
```python
# The coupling that makes validation MANDATORY:
CORSMiddleware,
allow_origins=settings.cors_origin_list,
allow_credentials=settings.CORS_ORIGINS != "*",
```
```python
if origins == ["*"]:
    return

https_re = re.compile(r"^https://[A-Za-z0-9.\-]+(:\d+)?$")
local_http_re = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")

for origin in origins:
    if origin == "*":
        raise RuntimeError(
            "AWAITHUMANS_CORS_ORIGINS contains '*' alongside explicit "
            "origins. Browsers reject this combination, and our auth "
            "middleware would flip credentials ON because the list "
            "isn't a bare '*'. ...")
    if https_re.match(origin) or local_http_re.match(origin):
        continue
    raise RuntimeError(
        f"AWAITHUMANS_CORS_ORIGINS contains an unsafe origin: '{origin}'. ...")
```

**Flow:** app factory → secret checks → `_validate_public_url(PUBLIC_URL)` → `_validate_cors_origins(cors_origin_list)` → FastAPI() → CORSMiddleware with the credentials coupling. Because `allow_credentials = (CORS_ORIGINS != "*")`, ANY narrowing of the list silently enables cookie-bearing cross-origin responses — so the validator is the only thing standing between an operator typo and session ride.
**Invariant:** Exactly three accepted origin families: bare `["*"]` alone, strict `https://host(:port)?`, and `http://localhost(:port)?`/`http://127.0.0.1(:port)?` for dev. Mixed `*`+explicit, plain http:// non-local, missing scheme, or path-bearing origins refuse to start. PUBLIC_URL accepts only scheme+host+optional-port (+optional trailing slash) because every constructed URL does `f"{PUBLIC_URL.rstrip('/')}/path"` — a pasted full OAuth callback URL stacks paths onto all of them. Both errors name the env var AND the fix.
**Probe:** `packages/python/tests/core/test_cors_validation.py` — `test_wildcard_mixed_with_explicit_refused` (:58–62) pins RuntimeError match="alongside explicit"; `test_plain_http_non_local_refused` (:51–55) pins "unsafe origin"; `TestPublicUrlValidation.test_full_oauth_callback_url_refused` (:105–111) pins match="not a base URL"; acceptance pins :22–45 and :88–103.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "CORS origin validation", limit: 10 });
// rank −18.44 → packages/python/awaithumans/server/app.py _validate_cors_origins 483-524;
// −25.65 → core/config.py Settings.cors_origin_list 219-223
```

## Verdict
Adopt validate-at-boot-with-RuntimeError over the credentials-coupling trap and the regex shape grammar; adapt the env-var names and error wording to your host; omit the Slack-callback-specific examples (keep the general no-path rule). Direct tests exist and were read in full; pytest execution is BLOCKED in this lane (no sqlmodel/fastapi venv) — probes are deterministic source assertions.
