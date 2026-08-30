<!-- capsule-v2 -->
# Webhook URL admission gate — what must be true of a webhook target at create/update time, before any delivery is attempted?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** how do you stop self-referential and disallowed-domain webhooks at the API boundary — including the PATCH-path context bug class?

## WebhookSerializer._validate_webhook_url
**Path/Symbol:** `apps/api/plane/app/serializers/webhook.py`:`WebhookSerializer._validate_webhook_url` (:27–55) + `create`/`update` (:57–66); model validators `apps/api/plane/db/models/webhook.py`:`validate_schema`/`validate_domain` (:21–31).
**Signature:** `_validate_webhook_url(self, url) -> None` (raises DRF `ValidationError`); called unconditionally from `create`, and from `update` only when a new `url` is present.
**Data Shape:** config inputs `settings.WEBHOOK_ALLOWED_IPS`, `WEBHOOK_ALLOWED_HOSTS`, `WEBHOOK_DISALLOWED_DOMAINS`; request host extracted from `self.context["request"]`.

### Decisive source
```python
try:
    validate_url(url, allowed_ips=settings.WEBHOOK_ALLOWED_IPS,
                 allowed_hosts=settings.WEBHOOK_ALLOWED_HOSTS)
except ValueError as e:
    raise serializers.ValidationError({"url": "Invalid or disallowed webhook URL."})

hostname = (urlparse(url).hostname or "").rstrip(".").lower()
if hostname in settings.WEBHOOK_ALLOWED_HOSTS:
    return                       # trusted hosts bypass the domain check
disallowed_domains = list(settings.WEBHOOK_DISALLOWED_DOMAINS)
if request:
    request_host = request.get_host().split(":")[0].rstrip(".").lower()
    disallowed_domains.append(request_host)     # loop-back guard: no self-webhooks
if any(hostname == domain or hostname.endswith("." + domain) for domain in disallowed_domains):
    raise serializers.ValidationError({"url": "URL domain or its subdomain is not allowed."})
```

**Flow:** SSRF resolution check → trusted-host early return → suffix-match against disallowed domains ∪ the instance's own host → reject. Model-level `validate_schema` (http/https only) and `validate_domain` (localhost/127.0.0.1 literal ban) give defense-in-depth below the serializer; `secret_key`/`workspace`/`deleted_at` are read-only; uniqueness of `(workspace, url)` enforced conditionally `WHERE deleted_at IS NULL`.
**Invariant:** admission runs on BOTH create and update paths — and the update path works only if the view passes `context={"request": request}`; without the request in context the loop-back guard silently disappears. This exact bug class is GHSA-pinned.
**Probe:** `tests/unit/bg_tasks/test_ssrf_advisories.py::TestWebhookPatchContextGuard::test_request_host_is_blocked_when_context_present` (:115–122, own-host webhook rejected when context present) + `test_unrelated_public_host_passes_with_context` (:124–128). Not executed this lane (no Django deps); advisory file read :100–129 directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "webhook serializer validate url disallowed domain create update", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `db/models/webhook.py::validate_domain` #1 and `WebhookSerializer._validate_webhook_url` :27–55 #2.

## Verdict
Admit-at-boundary + enforce-at-delivery as two independent gates (this capsule + pinned-fetch capsule); adopt the own-host suffix guard and read-only secret key; adapt domain lists/config plumbing; omit DRF serializer idioms if your framework differs.
