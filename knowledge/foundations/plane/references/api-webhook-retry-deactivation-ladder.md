<!-- capsule-v2 -->
# Webhook retry + auto-deactivation ladder — which failures retry, which deactivate, and which just get recorded?

**Source:** Plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** a delivery can fail as transport error, as SSRF-rejected URL, or as an unexpected bug — what should each outcome do to the webhook's lifecycle?

## webhook_send_task error triage
**Path/Symbol:** `apps/api/plane/bgtasks/webhook_task.py`:`webhook_send_task` (:235–389, triage half) + `send_webhook_deactivation_email` (:172–232) + `save_webhook_log` (:93–122).
**Signature:** decorator `autoretry_for=(requests.RequestException,), retry_backoff=600, retry_jitter=True, max_retries=5`.
**Data Shape:** every arm writes one `WebhookLog` row (request/response snapshot + `retry_count=self.request.retries`); terminal states are {delivered, exhausted→deactivated, url-rejected, swallowed-bug}.

### Decisive source
```python
except requests.RequestException as e:
    save_webhook_log(..., response_status=500, response_body=str(e), ...)
    if self.request.retries >= self.max_retries:
        Webhook.objects.filter(pk=webhook.id).update(is_active=False)
        send_webhook_deactivation_email.delay(webhook_id=webhook.id,
            receiver_id=webhook.created_by_id, reason=str(e), current_site=current_site)
        return
    raise requests.RequestException()      # celery autoretry honors backoff+jitter

except ValueError as e:
    # SSRF validation failure ... Not retryable — record it so the failure is
    # visible to the admin, but do not raise (no Celery retry) and do not
    # auto-deactivate (the cause may be transient DNS).
    save_webhook_log(..., response_status=400, response_body=f"Webhook URL rejected: {e}", ...)
    return
```

**Flow:** transport failure → log(500) → rethrow to Celery autoretry (600 s backoff × jitter, ≤5 retries) → at exhaustion flip `is_active=False` and email the creator with a deep link into workspace settings. SSRF/unresolvable rejection (`ValueError`) → log(400), no retry, no deactivation — transient DNS must not kill a webhook. Any other exception → `log_exception`, silent return. Log-write failures themselves are logged and swallowed: observability never breaks delivery.
**Invariant:** deactivation is reachable ONLY through the exhausted-transport path; a rejected URL is visible but non-fatal; every attempt leaves exactly one WebhookLog row with its retry count.
**Probe:** source-pinned whole-file read of webhook_task.py :235–389 this pass (no dedicated unit suite for the ladder at pin — honest caveat); deactivation email task :172–232 read whole-file (config from `get_email_configuration()`, HTML template `emails/notifications/webhook-deactivate.html`, plain-text derived).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "webhook deactivation email auto deactivate failed requests", limit: 10, fields: ["signature", "name", "file"] });
```
Observed live at pass 2: ranks `send_webhook_deactivation_email` :172–232 #1, `webhook_send_task`/`save_webhook_log` in top rows.

## Verdict
Adopt the three-arm triage (retryable transport / record-only rejection / swallow bug), exhaustion-triggered deactivation + owner notification, and always-log-with-retry-count; adapt backoff constants and the email template to your stack; omit Django mail-connection specifics.
