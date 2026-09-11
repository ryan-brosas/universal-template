<!-- capsule-v2 -->
# Webhook delivery envelope + HMAC signature — what exactly goes on the wire and how is it signed?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** how do you build a stable, verifiable webhook payload — including JSON-encoding hazards before signing?

## webhook_send_task payload construction
**Path/Symbol:** `apps/api/plane/bgtasks/webhook_task.py`:`webhook_send_task` (:242–338, envelope/signing half).
**Signature:** `@shared_task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=600, max_retries=5, retry_jitter=True)` → `webhook_send_task(self, webhook_id, slug, event, event_data, action, current_site, activity)`.
**Data Shape:** wire body `{event, action, webhook_id, workspace_id, workspace_slug, data, activity}`; headers `Content-Type: application/json`, `User-Agent: Autopilot`, `X-Plane-Delivery: <uuid4>`, `X-Plane-Event: <event>`, optional `X-Plane-Signature: <hmac-sha256 hex>`.

### Decisive source
```python
event_data = json.loads(json.dumps(event_data, cls=DjangoJSONEncoder)) if event_data is not None else None
action = {"POST": "create", "PATCH": "update", "PUT": "update", "DELETE": "delete"}.get(action, action)
payload = {"event": event, "action": action, "webhook_id": str(webhook.id),
           "workspace_id": str(webhook.workspace_id), "workspace_slug": slug,
           "data": event_data, "activity": activity}
if webhook.secret_key:
    hmac_signature = hmac.new(webhook.secret_key.encode("utf-8"),
                              json.dumps(payload).encode("utf-8"),
                              hashlib.sha256)
    headers["X-Plane-Signature"] = hmac_signature.hexdigest()
```

**Flow:** re-load the Webhook row in the worker (task args carry only ids) → DjangoJSONEncoder round-trip normalizes datetimes/UUIDs to strings BEFORE serialization → normalize HTTP verb to CRUD semantics → assemble envelope → sign the exact serialized bytes with HMAC-SHA256 under the per-webhook `secret_key` (`plane_wh_` + uuid4hex, default at model level) → POST once through `pinned_fetch` (redirects never followed).
**Invariant:** the signature covers the exact bytes sent (serialize first, then sign that string); encoding normalization happens BEFORE signing so receiver verification can't diverge on datetime/UUID shapes; delivery id is per-attempt fresh uuid4.
**Probe:** no dedicated unit test exists for the envelope at pin (apps/api suites cover the SSRF layer) — deterministic source pins instead: `webhook_send_task` :275–304 read whole-file this pass; signature header consumption mirrored by `X-Plane-Signature` docs in serializer/model reads. Honest caveat: behavior pinned by source only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "webhook delivery send retry", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2 (first search of the pass): ranks `webhook_send_task` :242–389 #1, `send_webhook_deactivation_email` :172–232 #2, `save_webhook_log` :93–122 top rows.

## Verdict
Adopt serialize→sign-the-exact-bytes ordering, verb normalization, and the id-only task-args pattern; adapt the encoder to your framework's JSON canonicalization; omit Plane's specific header names if your receivers already expect another convention.
