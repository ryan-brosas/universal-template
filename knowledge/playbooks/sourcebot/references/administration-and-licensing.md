# Administration, audit, email and licensing

Use an authorized Owner account for administration. A request to learn Sourcebot
or investigate code does not authorize inviting/removing users, changing sharing,
creating credentials, activating subscriptions or altering retention.

## Transactional email

Set `EMAIL_FROM_ADDRESS` plus either `SMTP_CONNECTION_URL` or individual
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME` and `SMTP_PASSWORD` values. The URL wins
if both forms are present; avoid accidental stale credentials in the losing form.
Email serves sign-in codes, invitations and join-request notifications. Email-code
login also needs its Security setting enabled; SMTP configuration alone does not
activate it. Verify a requested configuration with an approved recipient, not an
unsolicited email to a real member.

## Audit and Analytics

Paid audit logging defaults enabled via `SOURCEBOT_EE_AUDIT_LOGGING_ENABLED`.
Records live in PostgreSQL. A daily job removes entries older than
`SOURCEBOT_EE_AUDIT_RETENTION_DAYS`, default 180; `0` disables pruning. Indefinite
retention changes storage and privacy obligations. The sizing guide estimates
about 350 bytes per event; API/MCP-heavy workflows can produce many more events
than ordinary web use.

Owner-only `GET /api/ee/audit` accepts `since`/`until` timestamps and pagination;
see [the REST reference](api.md). The audit guide's single-org example supplies
`X-Org-Domain: ~` and `X-Sourcebot-Api-Key`; follow the installed API contract and
actual organization rather than assuming the example's domain is universal.

Records include ID, timestamp, action, actor ID/type, target ID/type, Sourcebot
version, metadata and organization ID. Actors can be users or API keys. The
action schema spans credential lifecycle/authentication failures, searches,
navigation, file reads, Ask chats, chat sharing/visibility/deletion, sign-in/out,
invitations/approval, membership/roles and audit access. Use the published schema
for exact action enums rather than maintaining another copied enum list here.
Metadata may contain messages, emails or key-related information; redact it
appropriately. One example omits `metadata` although the schema requires it:
validate actual responses rather than inferring guarantees from examples.

Analytics depends on these logs and their retention. A blank historical dashboard
may reflect disabled logging or pruning, not zero activity. After an authorized
change, verify a harmless event appears through audit retrieval and the relevant
Analytics view; console logs alone do not prove either.

## License activation and network requirements

The paid capability boundary is release-sensitive. In v5, Ask, MCP and role
management require paid access; specialized features may require additional
entitlements. Docs sometimes retain older Enterprise terminology. Check the
actual license response and current agreement, not a feature name alone.

| Activation route | Operational consequence |
| --- | --- |
| Online Activation Code | Default paid route; requires service pings. Seven days without a successful ping downgrades to free until a successful ping restores the subscription. |
| Offline License Key | Available on request; set `SOURCEBOT_EE_LICENSE_KEY`. Hard seat cap; increasing seats requires a new key, updated environment and restart. No online seat reconciliation. |
| Free trial | One 14-day trial per deployment, available in onboarding or Settings → License; no credit card required, service pings required. Expiry without payment downgrades to free while preserving data. |

Paid subscription expiry also downgrades features to free. Confirm plan state
before diagnosing an inaccessible feature as a transport bug. Do not retry
license-gated MCP calls or use an undocumented endpoint to evade that boundary.
The [service-ping and telemetry distinction](configuration-and-operations.md#logs-analytics-and-outbound-traffic)
matters for firewalls and privacy: opting out of product telemetry does not
satisfy or disable online activation's ping requirement.

## Seats and cancellation

Activation-code deployments can exceed purchased seats and reconcile additions.
The documented monthly policy prorates added seats; removals lower billing on
the next cycle. Standard yearly reconciliation invoices added seats quarterly
for remaining quarters. Offline keys enforce the purchased cap instead.
SCIM Pending membership is not the same as an activated billable seat; consult
[the lifecycle](identity-and-permissions.md#scim-membership-lifecycle).
Cancellation takes effect at the billing cycle/term boundary. Confirm the
customer's agreement before quoting pricing or making billing changes.

## Verification boundaries

Check saved SMTP configuration and delivery, permitted audit access and retention,
license state and reachability, or member/seat status according to the actual task.
A dashboard screenshot does not prove repository ACLs, and an online license does
not prove every optional feature is entitled. Keep secrets and organization data
out of reusable instructions.

## Official sources

- [Transactional email](https://docs.sourcebot.dev/docs/configuration/transactional-emails.md)
- [Audit logs and action schema](https://docs.sourcebot.dev/docs/configuration/audit-logs.md), [Analytics](https://docs.sourcebot.dev/docs/features/analytics.md), [sizing](https://docs.sourcebot.dev/docs/deployment/sizing-guide.md)
- [Activation](https://docs.sourcebot.dev/docs/activating-a-subscription.md), [trial](https://docs.sourcebot.dev/docs/free-trial.md), [seat reconciliation](https://docs.sourcebot.dev/docs/seat-reconciliation.md)
