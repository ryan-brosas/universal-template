<!-- capsule-v2 -->
# webhook-readback-oracle-containment — Why must a webhook's response body never appear in the raised error?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** Where does a delivery exception's message end up, and what can an untrusted HTTP endpoint do with that channel?

## Response-body containment + status ladder
**Path/Symbol:** `superset/reports/notifications/webhook.py:WebhookNotification.send` (:252-349) with `_sanitize_for_log`/`_LOGGED_RESPONSE_BODY_LIMIT` (:43-62).
**Signature:** `send(self) -> None` decorated `@backoff.on_exception(backoff.expo, NotificationUnprocessableException, factor=10, base=2, max_tries=5, max_time=120)` and `@statsd_gauge`.
**Data Shape:** status ladder: `>=500 ∨ ==429` → retryable `NotificationUnprocessableException`; `>=400` → non-retryable `NotificationParamException`; `>=300` → failure (redirects intentionally unfollowed via `allow_redirects=False`).

### Decisive source
```python
_LOGGED_RESPONSE_BODY_LIMIT = 500
# Response bodies are never folded into the exception message raised
# back to the caller -- that message is persisted verbatim as
# ``ReportExecutionLog.error_message`` and readable via the execution log
# API, which would otherwise turn the webhook target into a readback oracle
# for whatever it chooses to return (including an internal host reached via
# DNS rebinding).

if response.status_code >= 500 or response.status_code == 429:
    logger.warning(
        "Webhook to %s failed with status code %s: %s",
        wh_url, response.status_code,
        _sanitize_for_log(response.text[:_LOGGED_RESPONSE_BODY_LIMIT]),
    )
    raise NotificationUnprocessableException(
        f"Webhook failed with status code {response.status_code}"
    )
...
except requests.exceptions.RequestException as ex:
    raise NotificationUnprocessableException(str(ex)) from ex
```

**Flow:** feature-flag gate → URL validation (see webhook-peer-validation-toctou) → POST with per-request timeout and redirects disabled → on failure: body is control-character-escaped (`translate` over C0/C1 except tab — so the target cannot forge log lines) and truncated to 500 chars for **server-side logs only**; the raised message carries just the numeric status → execution-log persistence makes every raised message user-readable, hence the containment rule. Retry loop: only 5xx/429 re-enter backoff; the docstring documents that `max_time` samples elapsed *before* each attempt, so wall-clock can overshoot 120s by one request timeout plus jitter sleeps — deliberate trade to not abandon transient targets.
**Invariant:** Exception text crossing into persisted/user-readable surfaces must be derived from constants you control (status codes), never from remote-controlled bytes; anything remote-derived goes through sanitize+truncate into server-side logs. 3xx is failure because redirects are never followed.
**Probe:** `tests/unit_tests/reports/notifications/webhook_tests.py:678-710` (`test_send_error_message_omits_response_body`) injects `_LeakyResponse(status_code=502, text="internal-metadata-service-response-body")` and asserts the leaked body is absent from `str(excinfo.value)` while `"502"` is present.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "webhook send response body readback oracle status code notification", limit: 10 });
```

## Verdict
Adopt "log remotely-controlled bodies server-side only; raise constant-only messages" wherever errors persist into readable stores; adapt the sanitizer/truncation to your logging stack; omit the backoff decorator but preserve its documented pre-attempt elapsed semantics if you reuse `max_time`. Coverage: whole file read directly; direct test read at :678-710; file `no_recorded_issue`.
