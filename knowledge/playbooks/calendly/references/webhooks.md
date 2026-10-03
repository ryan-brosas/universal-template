# Webhooks and durable synchronization

## Subscribe at the correct boundary

`POST /webhook_subscriptions` requires `url`, `events`, `organization`, `scope`
and `webhooks:write`. `GET /webhook_subscriptions` requires organization and
scope filters; list/get/sample reads need `webhooks:read`. Delete an identified
subscription with `DELETE /webhook_subscriptions/{webhook_uuid}` only when the
integration is authorized to stop that stream.

Subscription scope is separate from OAuth scope:

- `organization`: events across the organization, subject to owner/admin rights.
- `user`: one user's events; also supply `user` and `organization`.
- `group`: one group's events; supply the matching group and organization and
  verify the caller's role permits the subscription.

The subscribed event family also needs its domain read grant:
`scheduled_events:read`, `routing_forms:read`, `contacts:read`, or
`meeting_recaps:read`. Webhooks require an eligible paid account. Routing-form
submission events are organization-only; meeting-recap events are user-only.
Create separate subscriptions when event families require different scopes.

The current reference covers invitee created/canceled, no-show created/deleted,
contact events and meeting-recap events as well as routing submissions. Read
exact event names from the create schema rather than expanding `contact.*` or
`meeting_recap.*` into guessed strings. Event-type events appear in the sample
endpoint and prose but are missing from the create-request enum: sample payload
availability does not establish subscribability.

`GET /sample_webhook_data` accepts event, organization and scope, with user/group
as applicable. Use samples as contract fixtures, not proof of live delivery.

## Verify before accepting work

For PAT-created subscriptions, provide a signing key even though the API marks
it optional. OAuth apps receive an application webhook signing key. Keep keys in
a secret store and map them to the correct subscription/app.

The header is `Calendly-Webhook-Signature: t=<unix-seconds>,v1=<hex>`:

1. Preserve the exact raw request-body bytes before JSON middleware changes
   them. Bound request size; parse the header and reject malformed values.
2. Compute HMAC-SHA256 with the signing key over the timestamp string, a literal
   period, then the raw body. Compare the expected and supplied signature bytes
   in constant time after validating their lengths/encoding.
3. Check timestamp freshness with a documented clock-skew policy. The vendor
   example uses a three-minute tolerance; also reject implausibly future-dated
   timestamps. Timestamp checks alone do not deduplicate valid repeated events.
4. After verification, parse and validate the envelope, durably accept the work,
   then return 2xx promptly. Complete slow work asynchronously. Do not acknowledge
   data you have failed to persist or enqueue.

The vendor's Node example reserializes `req.body`; its Ruby example reads raw
bytes. Do not rely on `JSON.stringify` preserving the signed representation.
Test valid signatures, changed whitespace/body, wrong keys, missing fields,
stale/future timestamps and duplicate deliveries against the actual receiver.

## Delivery and state

The documented timeouts are 10 seconds to connect and 15 seconds to read. For
3xx/4xx/5xx, the errors guide describes exponential retries for 24 hours “or until
24 hours after the booking of the event passes.” After 24 hours without another
successful message, the hook is disabled and must be recreated. One failed
message does not stop attempts to deliver others.

Monitor failures, latency, subscription `state` and `retry_started_at`. Confirm
replacement is authorized and avoid duplicate subscriptions when recreating a
disabled hook. Reconcile gaps with paginated API reads; webhook delivery is not
an exactly-once ledger.

The envelope has `event`, `created_at`, `created_by`, `payload`. Use the nested
payload, not an old sample's top-level `scheduled_event` access. Design durable
idempotent business transitions using resource URIs, event kind and relevant
source timestamps; do not invent a guaranteed delivery-ID header. Do not depend
on delivery order. Avoid logging whole payloads with invitee/contact PII.

## Rescheduling

A reschedule emits both `invitee.canceled` and `invitee.created`. The old invitee
has `rescheduled: true`; the new invitee is active. Correlate through invitee
URIs and `old_invitee`/`new_invitee`; these references belong to the invitee,
not the event. A plain cancellation has different meaning from a reschedule.

Exercise both arrival orders and duplicate deliveries. A delayed cancellation
for the old invitee must not cancel the newly active booking in your database.
When incomplete payloads or ordering leave doubt, retrieve the current invitee
and event before sending irreversible downstream actions.

Organization-scoped hooks can survive their creator's removal or demotion,
according to the FAQ; user-scoped hooks stop working when the user leaves the
organization. Reconcile subscriptions explicitly during offboarding rather than
assuming role changes clean up every stream.

## Sources

- [Create subscription](https://developer.calendly.com/api-docs/calendly-api/webhooks/create-webhook-subscription.md),
  [sample payloads](https://developer.calendly.com/api-docs/calendly-api/webhooks/get-sample-webhook-data.md).
- [Signatures](https://developer.calendly.com/api-docs/overview/webhooks/webhook-signatures.md),
  [errors/retries](https://developer.calendly.com/api-docs/overview/webhooks/webhook-errors.md),
  [timeouts](https://developer.calendly.com/api-docs/overview/webhooks/webhook-timeouts.md).
- [Reschedule lifecycle](https://developer.calendly.com/docs/api-guides/see-how-webhook-payloads-change-when-invitees-reschedule-events.md),
  [FAQ/offboarding](https://developer.calendly.com/docs/getting-started/frequently-asked-questions.md).
