<!-- capsule-v2 -->
# Notification status callbacks — how do provider delivery webhooks record failures without becoming retry amplifiers?

**Source:** healthchecks BSD-3-Clause `master@29b5ec251059034b79e0120e2ff0c3e35d7bd9f8`; Codebase Memory `healthchecks`. **Question:** When Twilio (or any provider) POSTs an async delivery outcome to a public webhook, how do you normalize unknown payloads, expire stale callbacks, and disable a channel only when the provider says so — while never giving the caller a reason to retry?

## Notification.status_url + views.notification_status
**Path/Symbol:** `hc/api/models.py:Notification.status_url` (:1349-1350), `hc/api/views.py:notification_status` (:816-852).
**Signature:** `status_url(self) -> str` (= `absolute_reverse("hc-api-notification-status", args=[self.code])`); `notification_status(request: HttpRequest, code: UUID) -> HttpResponse`.
**Data Shape:** Inbound POST keys understood: generic `error` (truncated to 200 chars) with optional `mark_disabled`; Twilio `MessageStatus ∈ {failed, undelivered}`; Twilio `CallStatus == "failed"`. Writes: `Notification.error` (update_fields), `Channel.last_error`, optionally `Channel.disabled=True`. Every path answers **200**.

### Decisive source
```python
# hc/api/views.py — TTL lookup; miss ⇒ 200 ON PURPOSE
cutoff = now() - td(hours=1)
notification = Notification.objects.get(code=code, created__gt=cutoff)
except Notification.DoesNotExist:
    # If the notification does not exist, or is more than a hour old,
    # return HTTP 200 so the other party doesn't retry over and over again:
    return HttpResponse()

error, mark_disabled = None, False
if request.POST.get("error"):
    error = request.POST["error"][:200]              # cap attacker-controlled text
    mark_disabled = bool(request.POST.get("mark_disabled"))
if request.POST.get("MessageStatus") in ("failed", "undelivered"):
    status = request.POST["MessageStatus"]
    error = f"Delivery failed (status={status})."
if request.POST.get("CallStatus") == "failed":
    error = "Delivery failed (status=failed)."

if error:
    notification.error = error
    notification.save(update_fields=["error"])
    channel_q = Channel.objects.filter(id=notification.channel_id)
    channel_q.update(last_error=error)
    if mark_disabled:                                # opt-in latch ONLY
        channel_q.update(disabled=True)
return HttpResponse()
```

**Flow:** Look up by notification UUID within a 1-hour window → normalize whichever provider vocabulary is present (generic keys take precedence; Twilio SMS and voice statuses map into the same error string) → on failure: persist the error onto the Notification row and fan it to the Channel's `last_error` via queryset `.update()` → latch `disabled` only when the payload's `mark_disabled` flag asked for it.
**Invariant:** Unknown/expired callbacks get 200-with-empty-body — a non-2xx here converts one lost callback into infinite provider retries. Success statuses ("delivered") write NOTHING: absence of error in storage IS the success representation. Disabling from the read-back plane is strictly opt-in per payload; contrast with the send-side ledger where only permanent TransportErrors may disable (channel-notify-ledger) — two independent latches, both conservative. Error text is capped at 200 chars before storage because it originates off-host. The 1-hour TTL also bounds how long a leaked status URL stays potent.
**Probe:** `hc/api/tests/test_notification_status.py::test_it_handles_twilio_failed_status` (:26-35, n.error AND channel.last_error set, channel still enabled), `::test_it_checks_ttl` (:57-66, 61-minute-old notification ignores the callback but still 200s), `::test_it_handles_missing_notification` (:68-72), `::test_it_handles_mark_disabled_key` (:89-98, disabled=True), `::test_it_handles_twilio_delivered_status` (:47-55, nothing written).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "notification status callback MessageStatus mark_disabled last_error", limit: 10 });
```

## Verdict
Adopt fail-open 200 semantics for all unmatchable callbacks, the TTL-bounded lookup, payload-vocabulary normalization into one stored error string, and per-payload opt-in disabling. Adapt provider key names and the TTL constant to your providers' actual retry policies. Omit the CallStatus arm if you carry no voice transport — keep the truncation cap regardless: callback bodies are hostile input.
