<!-- capsule-v2 -->
# Action-matching webhook dispatcher — how do you fan a domain event out to registered HTTP endpoints?

**Source:** easy!Appointments GPL-3.0 `main@359c3649dc1977fa3fe882b422a462d77c8abce4`; Codebase Memory `ext-easyappointments`. **Question:** How are webhooks registered, matched to actions, authenticated, and isolated from request failures?

## Webhooks_client trigger/call
**Path/Symbol:** `application/libraries/Webhooks_client.php:54` (`trigger`, 54–65) and `:74` (`call`, 74–105).
**Signature:** `trigger(string $action, array $payload): void`
**Data Shape:** Webhook rows: `{id, name, url, actions (comma-separated string), secret_header, secret_token, is_ssl_verified (bool cast), notes, is_active}`. Wire envelope: `{"action": <string>, "payload": <array>}`.

### Decisive source
```php
// application/libraries/Webhooks_client.php:58-63 — comma-list membership match
foreach ($webhooks as $webhook) {
    $actions = array_filter(array_map('trim', explode(',', (string) $webhook['actions'])));
    if (in_array($action, $actions, true)) {
        $this->call($webhook, $action, $payload);
    }
}
// :81-92 — optional custom auth header + per-webhook SSL toggle
if (!empty($webhook['secret_header']) && !empty($webhook['secret_token'])) {
    $headers[$webhook['secret_header']] = $webhook['secret_token'];
}
$response = $client->post($webhook['url'], [
    'verify' => $webhook['is_ssl_verified'], 'headers' => $headers,
    'json' => ['action' => $action, 'payload' => $payload],
]);
```

**Flow:** 18 action constants (`application/config/constants.php:138-155`: `appointment_save/delete`, `unavailability_save/delete`, `customer_save/delete`, `service_save/delete`, `service_category_save/delete`, `provider_save/delete`, `secretary_save/delete`, `admin_save/delete`, `blocked_period_save/delete`) are fired from ~30 controller call sites AFTER the DB write succeeds — e.g. `Calendar.php:398` fires `WEBHOOK_APPOINTMENT_SAVE` post-save, post-sync, post-notification.
**Invariant:** dispatch is **synchronous, in-request, fail-open**: each POST runs inside try/catch that only logs (`log_message('error', …)` + trace); one dead endpoint never fails the user operation and never blocks later webhooks. The `secret_header` NAME is caller-chosen (not fixed like `X-Webhook-Signature`) and the token travels verbatim (no HMAC body signing). PORTER TRAP: `is_active` exists on the schema/API but `trigger()` loads ALL webhooks and matches actions only — filtering by `is_active` is left to whatever writes the row; do not assume the dispatcher skips inactive hooks.
**Probe:** `grep -c "in_array(\$action, \$actions, true)" application/libraries/Webhooks_client.php` (= 1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-easyappointments", query: "trigger webhook", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt comma-action matching + envelope + custom-header secret + swallow-and-log delivery; adapt Guzzle to your HTTP client keeping `'verify' => is_ssl_verified`; omit the missing `is_active` filter ONLY after deciding it's a bug you're not inheriting. Direct tests: none upstream.
