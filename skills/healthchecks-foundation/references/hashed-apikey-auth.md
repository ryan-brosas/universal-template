<!-- capsule-v2 -->
# Hashed API keys — prefix-index lookup with HMAC verification and a plaintext fallback ladder

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you rotate from plaintext API keys to hashed-at-rest keys without downtime, and what does the read-only flag change in the request pipeline?

## ProjectManager.for_api_key / _make_api_key / compare_api_key + decorators
**Path/Symbol:** `hc/accounts/models.py:ProjectManager.for_api_key` (:397-440), `Project._make_api_key` (:538-556), `compare_api_key` (:581-593); `hc/api/decorators.py:authorize` (:33-68), `authorize_read` (:71-93), `_get_api_version` (:25-30), `cors` (:96-120).
**Signature:** `for_api_key(api_key: str, accept_rw: bool, accept_ro: bool) -> Project | None`; `_make_api_key(prefix) -> tuple[key, key_hash]`; `compare_api_key(key: str) -> bool`.
**Data Shape:** Wire format `hcw_<21-char-urlsafe>` (write) / `hcr_...` (read-only); stored hash = `<first-8-of-secret>.<hex(HMAC-SHA256(SECRET_KEY, key))>` (72 chars). Legacy rows store the plaintext key directly. Decorators attach `request.project / request.readonly / request.v`.

### Decisive source
```python
# hc/accounts/models.py — lookup by 8-char prefix, then constant-time verify
if accept_rw and api_key.startswith("hcw_"):
    secret8 = api_key[4:12]
    for project in Project.objects.filter(api_key__startswith=secret8):
        if project.compare_api_key(api_key):
            return project
...
def compare_api_key(self, key):
    ...
    # Only calculate and compare digest if db key length is 8 + 64 = 72
    if "." not in expected:
        return False          # plaintext-era key: never HMAC-compared
    _, key_hash = expected.split(".", maxsplit=1)
    digest = hmac.digest(settings.SECRET_KEY.encode(), key.encode(), "sha256")
    return hmac.compare_digest(digest.hex(), key_hash)

# hc/api/decorators.py — write endpoints refuse ro keys BEFORE any project logic
project = Project.objects.for_api_key(api_key, accept_rw=True, accept_ro=False)
...
request.readonly = (
    api_key.startswith("hcr_") or api_key == request.project.api_key_readonly
)
```

**Flow:** authorize() (write): parse body once into request.json (shared with views), accept key from X-Api-Key header or json body, require exactly 32 chars, look up RW-only. authorize_read(): header-only, accepts both key classes, computes readonly flag; read endpoints then shape their payloads via check.to_dict(readonly=...) which swaps uuid/ping_url/update_url for unique_key and omits channel lists — plus get_checks skips prefetching channels entirely when readonly (query-budget discipline pinned by assertNumQueries(2)). API version comes from the URL path (v1/v2/v3 share one urlconf include) and gates wire details like started-vs-status.
**Invariant:** The 8-char prefix is an INDEX PROBE, not an auth factor — full verification is always compare_digest over the full HMAC; that's what lets hashed and legacy plaintext rows coexist in one column without a migration flag. The "." sentinel check makes "is this row hashed?" a byte test rather than schema. A wrong-length key short-circuits to 401 before ANY db hit. Test test_it_does_not_compare_digest_to_plaintext_path pins that a plaintext row must NOT reach hmac.compare_digest — the era-detection is load-bearing both ways.
**Probe:** `hc/api/tests/test_auth.py::test_ro_endpoint_accepts_hashed_readonly_key`, `test_rw_endpoint_rejects_hashed_readonly_key`, `hc.accounts.models hmac.compare_digest patch test :62-73`, `hc/api/tests/test_list_checks.py::test_readonly_key_works` (assertNumQueries(2) + no uuid leak).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "for_api_key api key readonly authorize", limit: 10 });
```
Resolves line-exact: ProjectManager.for_api_key and decorator pins in test_auth.py.

## Verdict
Adopt prefix-probe + full-HMAC-verify dual-era storage, header/body key extraction parsed once, and readonly shaping at serialization time. Adapt prefixes, HMAC key source, and version routing. Omit the plaintext fallback only after a hard cutover you control — the code path exists precisely because you can't always.
