<!-- capsule-v2 -->
# Slug ping auto-provisioning — create-on-miss with 2× limit headroom and ambiguity as a first-class response

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do slug-addressed pings support "just POST to the URL and it exists" ergonomics without letting one project spam-create checks or two same-slug checks corrupt routing?

## views.ping_by_slug + Spec.unique/_lookup (API twin)
**Path/Symbol:** `hc/api/views.py:ping_by_slug` (:247-287), `guess_kind` (:53-58), API idempotent-create `_lookup` (:290-312) / `_update` channels ladder (:315-411), `hc/accounts/models.py:set_ping_key` (:568-579).
**Signature:** `ping_by_slug(request, ping_key: str, slug: str, action="success", exitstatus=None)`; `?create=1` query toggles provisioning; response 200/201/400/404/409.
**Data Shape:** ping_key = project-level 22-char [a-z0-9] secret (token_urlsafe(16).lower(), "-" "_" stripped for email-address aesthetics); slug lowercase-enforced (`slug != slug.lower()` → 400); check_limit headroom = `num_checks_used() >= check_limit * 2 → 404`.

### Decisive source
```python
# hc/api/views.py — three failure modes are THREE different responses
try:
    check = Check.objects.get(slug=slug, project__ping_key=ping_key)
except Check.DoesNotExist:
    if request.GET.get("create") != "1":
        return HttpResponseNotFound("not found")
    ...
    if profile.num_checks_used() >= profile.check_limit * 2:
        return HttpResponseNotFound("not found")
    check = Check(project=project, name=slug, slug=slug)
    check.save()
    check.assign_all_channels()
    created = True
except Check.MultipleObjectsReturned:
    return HttpResponse("ambiguous slug", status=409)
...
if response.status_code == 200 and created:
    response.content = b"Created"
    response.status_code = 201
```

**Flow:** Resolve by (ping_key→project, slug→check) → miss + create=1 + under 2× limit → create, name=slug, assign ALL project channels (new check pages everyone immediately) → wrap in ping() and upgrade 200→201 only when the ping itself succeeded. The API's Spec.unique mechanism solves the same determinism problem for script-created checks: _lookup requires EVERY unique-referenced field to be present-and-non-null else creates fresh — no silent adoption of a mismatching check.
**Invariant:** Ambiguity is surfaced (409 "ambiguous slug"), never resolved silently by first-match — a duplicate slug is a user configuration bug you must make visible. The 2× multiplier means auto-provisioning degrades gracefully: legitimate users over-limit can still be created INTO their existing budget twice before hard refusal; plain 404 on refusal avoids confirming limit state to anonymous posters. Channel auto-assignment at creation is what makes "create=1 then it alerts" coherent. Uppercase slugs fail EARLY with "invalid url format" because URLs that survive round-trips must not depend on case-preserving proxies.
**Probe:** `hc/api/tests/test_ping_by_slug.py::test_it_auto_provisions_missing_check` (201 Created, channels assigned), `test_auto_provisioning_limits_check_count`, `test_it_handles_duplicates` (409), `test_it_rejects_uppercase_slug`, plus `hc/api/tests/test_create_check.py::test_it_creates_new_check_if_unique_references_absent_field`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "ping_by_slug create slug ambiguous provisioning", limit: 10 });
```

## Verdict
Adopt create-on-miss gated by soft-limit headroom, 409-on-ambiguity over silent pick, post-ping 201 promotion, and all-channel default assignment for provisioned monitors. Adapt key/slug grammar and limits. Omit the API-side unique twin if you have no machine-writer surface — but keep "never guess which existing resource an ambiguous address meant".
