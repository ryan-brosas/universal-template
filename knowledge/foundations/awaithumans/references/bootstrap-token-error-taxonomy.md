<!-- capsule-v2 -->
# One-Shot Bootstrap Token & ServiceError Taxonomy — how does first-run operator creation stay un-brickable, and how do service errors reach HTTP without per-exception handlers?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you run a one-shot first-credentials flow that a crash/restart can't strand or brick — and surface every service error as structured HTTP?

## In-memory single-use token + class-attribute-driven error envelope
**Path/Symbol:** `packages/python/awaithumans/server/core/bootstrap.py` — `ensure_token` (:55–64), `verify_token` (:67–74), `mark_complete` (:76–81), `is_active` (:84–87), `log_setup_banner` (:92+); `packages/python/awaithumans/server/services/exceptions.py` — `ServiceError` base (:14–31), 17 subclasses; `packages/python/awaithumans/server/core/exceptions.py:21–52` — the two handlers. Tests: `packages/python/tests/auth/test_setup_bootstrap.py`, `packages/python/tests/embed/test_exceptions.py`.
**Signature:** module functions over `_lock: threading.Lock`, `_token: str | None`, `_completed: bool`; `ServiceError.status_code / error_code / docs_path` are CLASS attributes each subclass overrides in three lines.
**Data Shape:** setup routes answer `{needs_setup, token_active}`; errors leave as `{error, message, docs}` JSON with the subclass's status_code.

### Decisive source
```python
def ensure_token() -> str:
    with _lock:
        if _completed:
            raise RuntimeError("Bootstrap already completed in this process.")
        if _token is None:
            _token = secrets.token_urlsafe(_BOOTSTRAP_TOKEN_BYTES)
        return _token

def verify_token(supplied: str) -> bool:
    with _lock:
        if _completed or _token is None:
            return False
        return hmac.compare_digest(supplied, _token)   # constant-time
# mark_complete(): _completed = True; _token = None  → token can NEVER be
# re-derived after setup (one-shot), and restart-before-setup regenerates.

# core/exceptions.py — ONE handler for ALL ServiceErrors:
return JSONResponse(status_code=exc.status_code,
                    content={"error": exc.error_code,
                             "message": exc.message, "docs": exc.docs_url})
```

**Flow:** startup checks `count_users()==0` → ensure_token generates once per empty-DB process and prints the copy-this-URL banner DIRECTLY to stdout (`sys.stdout.write`, not logger — must survive log filters/pipes) plus a WARNING duplicate for journald/Docker followers → `/setup?token=…` verifies via compare_digest → first operator created → mark_complete clears token permanently; setup routes then 410 Gone forever. The taxonomy side: every service raise is a tiny subclass setting exactly three class attributes; the handler map `{ServiceError: …, Exception: …}` needs no per-exception registration.
**Invariant:** (1) Token lives ONLY in process memory — deliberate: crash before setup ⇒ fresh token on restart (no stale creds to recover); after setup it's cleared for process lifetime, so a leaked log token dies at completion. (2) `verify_token` returns False both before generation AND after completion (fail-closed). (3) Banner must bypass logging entirely or an operator who pipes stdout never sees the URL. (4) Error semantics live ON THE CLASS (409 LAST_OPERATOR "last active operator must remain", 422 USER_NO_ADDRESS "unreachable user", distinct VERIFIER_API_KEY_MISSING vs VERIFIER_ENDPOINT_MISSING because 'key missing' when the endpoint is unset is a documented 30-minute debugging detour); docstrings carry WHY so porters keep distinctions instead of collapsing them.
**Probe:** `packages/python/tests/auth/test_setup_bootstrap.py` — `test_bootstrap_module_is_idempotent` (:128: t1==t2), `test_bootstrap_verify_rejects_after_complete` (:143: verify True→False around mark_complete), second-bootstrap 409 (:101); route-level matrix :33–125 incl. middleware-bypass check. `tests/embed/test_exceptions.py` pins the envelope shape end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "ensure_token verify_token mark_complete ServiceError status_code error_code", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the in-memory one-shot bootstrap trio (idempotent generate, fail-closed constant-time verify, permanent clear) and the class-attribute ServiceError→single-handler mapping verbatim — both are the cheapest correct shapes for their problems. Adapt banner cosmetics and the error catalog to your domain, but keep config-vs-auth-vs-provider distinctions separate (the docstrings document real support cost when collapsed).
