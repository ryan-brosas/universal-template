<!-- capsule-v2 -->
# Deferred email dispatch — why does every side-effectful mutation send mail through after()?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** When do emails fire relative to the DB commit, and what isolation/branding rules must each send preserve?

## after()-based send ladder across routers
**Path/Symbol:** `apps/web/src/trpc/routers/polls.ts` (make :227–239, book :1015–1077), `apps/web/src/trpc/routers/polls/participants.ts` (add :361–387), `apps/web/src/trpc/routers/polls/comments.ts` (add :157–170); notification targeting `apps/web/src/features/notifications/data.ts:getNotificationRecipient`; transport `packages/emails/src/send.tsx`.
**Signature:** `after(async () => sendXEmail({...}))` — Next.js serverless post-response work; every send resolves branding first (`getInstanceBranding()` or `getSpaceBranding(space)`).
**Data Shape:** emails carry `{to, locale, branding, props}` (+replyTo for response notifications; +icalEvent attachment on booking).

### Decisive source
```ts
after(() =>
  sendNewResponseNotificationEmail({
    pollId, pollTitle: participant.poll.title, participantName: participant.name,
    participantEmail: participant.email, note: participant.note,
    excludeUserId: ctx.user.id,
  }),
);
```
```ts
try {
  const recipient = await getNotificationRecipient({ pollId, type: "poll.response.submitted", excludeUserId: ctx.user.id });
  if (!recipient) return;
  /* ... send ... */
} catch (err) {
  logger.error({ error: err, pollId }, "Failed to send new response notification email");
}
```

**Flow:** mutation commits → after() callback runs post-response → recipient resolved fresh (muted owners and the actor excluded via excludeUserId) → branding chosen per scope (space branding when the poll lives in a space, else instance branding) → locale from the RECIPIENT's stored preference. Booking additionally attaches the same ICS blob to host AND participant mails.
**Invariant:** no email send can fail a mutation (they're outside the response path AND wrapped in catch-log); the ACTING user is always excluded from their own notifications; per-recipient locale/timeZone is read at send time from captured rows, not the request context which is long gone.
**Probe:** deterministic grep anchors: `grep -c 'after(' apps/web/src/trpc/routers/polls/participants.ts` → 2; `grep -n 'excludeUserId' apps/web/src/features/poll/data.ts apps/web/src/trpc/routers/polls/comments.ts | grep -c excludeUserId` → ≥2 lines total.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "sendNewPollEmail getInstanceBranding after", limit: 5 });
```

## Verdict
Adopt the after()+catch-log+recipient-resolution pattern verbatim; adapt to your task queue if not serverless (after() ≈ enqueue); omit template internals. Source-pinned; no direct test.
