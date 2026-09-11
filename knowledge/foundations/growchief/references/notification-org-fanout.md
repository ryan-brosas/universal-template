<!-- capsule-v2 -->
# Notification org fan-out — how does one backend event become a per-user inbox row (and optional email) for a whole organization?

**Source:** growchief AGPL-3.0 `main@abb1e37a6f5595d8d105aef5871a2eeb0c22a1dc`; Codebase Memory `growchief`. **Question:** when an automation event must reach every member of an org, what fans out, in what concurrency order, and through which dispatch planes?

## Connected graph-selected seam
**Path/Symbol:** `shared/server/notifications/notification.manager.ts:NotificationManager.sendNotification` (:13–33); dispatch planes: `apps/orchestrator/src/workflows/workflow.throttle.ts:290–297` (Temporal `proxyActivities<NotificationActivity>` :72 → activity :10–22) and `shared/server/database/bots/bots.service.ts:240–248` (direct in-process from `loggedOut`); persistence: `shared/server/database/notifications/notifications.repository.ts:38–62`.
**Signature:** `sendNotification(organizationId: string, title: string, message: string, sendEmail = false): Promise<void>`.
**Data Shape:** Input = org id + title + message (+ email flag). DB row per user = `{userId, title, content, additionalInfo?, read: false}`; email = same title/message to each member address.

### Decisive source
```ts
const orgUsers =
  await this._organizationService.listUsersPerOrganization(organizationId);
await Promise.all(
  orgUsers.map((p) =>
    this._notificationService.createNotification(p.user.id, title, message),
  ),
);
if (!sendEmail) return;
for (const user of orgUsers) {
  await this._emailService.sendEmail(user.user.email, title, message);
}
```

**Flow:** event origin resolves the org → manager lists all org members once → **in-box rows fan out concurrently** (`Promise.all`, one `read:false` row per user) → if `sendEmail`, the same payload is emailed **sequentially** (`for…await`) — deliberate asymmetry: cheap local writes parallelize, provider-bound sends serialize. Dispatch planes differ by origin: the immortal throttler reaches it only as a Temporal activity (durability across worker restarts), while the API-side `loggedOut` handler calls the manager directly.
**Invariant:** one event ⇒ exactly one inbox row per org member; emails never precede persisted rows; `markAsRead`/`markAllAsRead` are tenant-scoped `updateMany` (`id+userId`, resp. `userId+read:false`) — a user can never flip another user's rows. The throttle-plane call is double-gated: `patched('notifications-01-09-2025') && restriction` (see throttler-replay-patching). Known wart to NOT port: `loggedOut`'s message body embeds a hardcoded `https://platform.postiz.com` link (bots.service :245) — upstream branding leak.
**Probe:** no upstream test runner exists (spec/test count = 0). Deterministic source pins: read `notification.manager.ts:13–33`; grep `sendNotification|NotificationActivity` → 10 hits with exact live sites throttle :72/:291 and bots.service :240; read `notifications.repository.ts:64–86` for the scoped updateMany pair.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "sendNotification notification manager", limit: 10, fields: ["signature", "lines"] });
// rank#1: NotificationManager.sendNotification notification.manager.ts:13-33; also NotificationActivity.sendNotification apps/orchestrator .../notification.activity.ts:10-22
```
Note: static CALLS edges into the manager are 0 — both real call sites go through Temporal's activity proxy or service-internal injection; verify liveness by source grep, not graph degree.

## Verdict
Adopt the list-once/fan-out shape with concurrent-row + sequential-email split and tenant-scoped read-marking. Adapt membership lookup (`listUsersPerOrganization`) and the two transport planes to your stack (e.g. queue job instead of Temporal activity). Omit the hardcoded product URL in message bodies and the `additionalInfo` free-text column unless you need structured deep-links. Coverage caveat: all four cited paths `no_recorded_issue`/`metadata_match`; no behavioral runner upstream.
