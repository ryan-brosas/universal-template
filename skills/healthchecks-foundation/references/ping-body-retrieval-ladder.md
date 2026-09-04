<!-- capsule-v2 -->
# Ping body retrieval ladder — how do you serve a logged request body back from a mixed S3/inline store?

**Source:** healthchecks BSD-3-Clause `master@29b5ec251059034b79e0120e2ff0c3e35d7bd9f8`; Codebase Memory `healthchecks`. **Question:** When ping bodies live sometimes inline and sometimes in object storage, how does the read path distinguish "expired", "absent", and "storage outage" without letting an outage clog the web tier?

## Ping.get_body_bytes + views.ping_body
**Path/Symbol:** `hc/api/models.py:Ping.get_body_bytes` (:749-769), `hc/api/views.py:ping_body` (:626-646).
**Signature:** `get_body_bytes(self) -> bytes | None`; `ping_body(request: ApiRequest, code: UUID, n: int) -> HttpResponse`.
**Data Shape:** Writer side (see ping-ingest-transaction): bodies >100 B with `S3_BUCKET` set go to S3 (`object_size` recorded), smaller ones inline in `body_raw`. Reader outputs four distinct outcomes: 403 wrong project / 404 outside retention or no body / 503 breaker-tripped or GetObjectError / 200 `text/plain` original bytes.

### Decisive source
```python
# hc/api/models.py — the S3 leg is circuit-breaker-gated
if self.object_size and self.n:
    # Do not attemt to touch S3 if we have recorded more than 3
    # errors ... in the last minute ... a S3 outage can clog our
    # requests handlers and cause a bigger issue.
    if not TokenBucket.s3_is_healthy():
        raise self.GetBodyError()
    try:
        return get_object(str(self.owner.code), self.n)
    except GetObjectError:
        TokenBucket.record_s3_get_object_error()
        raise self.GetBodyError()
if self.body_raw:
    return bytes(self.body_raw)
return None

# hc/api/views.py — retention gate BEFORE any body lookup
threshold = check.n_pings - profile.ping_log_limit
if n <= threshold:
    raise Http404()
...
try:
    body = ping.get_body_bytes()
except Ping.GetBodyError:
    return HttpResponse(status=503)      # outage ≠ absence
if not body:
    raise Http404()                      # absence ≠ outage
```

**Flow:** API-key ownership check (read-only keys rejected upstream → 401) → compute per-profile retention threshold `n_pings − ping_log_limit` and 404 anything at-or-below it WITHOUT touching S3 → fetch Ping row by `(owner, n)` → model method picks inline vs S3 leg → breaker/GetObjectError surfaces as 503 while genuinely-absent bodies stay 404 → stream raw bytes as text/plain.
**Invariant:** The three "cannot show it" causes map to THREE different status codes, and the retention check runs before storage access so expired-body requests never pay an S3 round-trip. The breaker check happens BEFORE get_object and the failure recording AFTER it — one flaky read both fails fast for this request and raises the water level for all subsequent ones (mechanics of the bucket itself: see tokenbucket-db-limiter; writer-side duality: see ping-ingest-transaction). Original bytes are returned unpadded/untranslated (`b"Hello\x01\x99World"` survives verbatim).
**Probe:** `hc/api/tests/test_get_ping_body.py::test_it_checks_n_threshold` (:56-62, n=1 with n_pings=101 → 404 under default limit 100), `::test_it_handles_unhealthy_s3` (:80-90, tokens=0.0 → 503), `::test_it_handles_s3_error` (:92-99, GetObjectError → 503 AND records), `::test_it_handles_no_body` (:64-69, 404), `::test_it_returns_original_bytes` (:71-78).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "ping body get_body_bytes object_size GetBodyError", limit: 10 });
```

## Verdict
Adopt the outcome ladder (retention-before-storage, outage-as-503-not-404) and the breaker-before-read/recorder-after-read ordering. Adapt the threshold formula to your retention model and swap S3 freely. Omit the breaker entirely only if your storage is transactional-local — but then keep bodies out-of-band anyway: inline-only stores grow without bound.
