<!-- capsule-v2 -->
# Webhook entry — what does a GitHub webhook endpoint owe GitHub?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** When a webhook receiver has no shared secret configured, should verification fail open or closed, and should handler exceptions ever escape as non-200 responses GitHub would retry?

## Signature gate + swallow-all wrapper
**Path/Symbol:** `sweepai/api.py:276-294` (`validate_signature`, `webhook`, `handle_request`); `sweepai/utils/hash.py:10-35` (`verify_signature`) (line range).
**Signature:** `async def validate_signature(request: Request, x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature-256"))` / `def verify_signature(payload_body: bytes, signature_header: str | None) -> bool`.
**Data Shape:** Raw request body bytes + `X-Hub-Signature-256` header; `WEBHOOK_SECRET` from server env. Returns bool or raises `HTTPException(403)`.

### Decisive source
```python
if not WEBHOOK_SECRET:
    # If the secret is not set, we can't verify the signature
    return True
if not signature_header:
    return False
...
if not hmac.compare_digest(expected_signature, signature_header):
    return False
```
```python
try:
    handle_github_webhook({"request": request_dict, "event": event})
except Exception as e:
    logger.exception(str(e))
logger.info(f"Done handling {event}, {action}")
return {"success": True}
```

**Flow:** `POST /` → dependency `validate_signature` (403 only when a secret IS configured AND header missing/mismatched) → `webhook` → `handle_request` wraps the full dispatch in try/except-log → always returns `{"success": True}`.
**Invariant:** With a secret set, mismatched payloads never reach handlers and comparison is constant-time. Without a secret, the endpoint is intentionally fail-OPEN (self-host convenience). Handler crashes are logged, never surfaced to GitHub — delivery retries are not a recovery mechanism here.
**Probe:** `sweepai/utils/hash.py` has no direct unit test (coverage caveat); deterministic check = read the three early returns in order: no-secret→True, no-header→False, compare_digest-miss→False. Executed at pin: buttons unit suite green proves importability of the web-events models this path shares.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "verify signature hmac payload body secret", limit: 8 });
// executed at pin: #1 sweep.sweepai.utils.hash.verify_signature hash.py 10-35,
// #2 sweep.sweepai.api.validate_signature api.py 276-282, EnvVar WEBHOOK_SECRET node present
```

## Verdict
Adopt the three-branch ladder (secret-absent posture must be an explicit decision, constant-time compare, missing header ≠ bad signature); adapt the FastAPI `Depends` wiring and loguru contextualize; omit Sweep's Sentry init/version-stamp side effects. Coverage caveat: `hash.py` and `api.py` are `no_recorded_issue` in graph coverage but have zero direct unit tests — port with your own HMAC tests.
