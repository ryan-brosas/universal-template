<!-- capsule-v2 -->
# Webhook click-event fast path — how do you gate per-click fan-out on a Redis set so high-traffic clicks skip DB lookups entirely?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** For an event stream as hot as link clicks, how do you decide "does anyone even listen?" without touching the primary database?

## ClickWebhookWorkspaces set + syncWorkspaceWebhookStatus
**Path/Symbol:** `apps/web/lib/webhook/click-webhook-workspaces.ts:ClickWebhookWorkspaces` (9-32) + `syncWorkspaceWebhookStatus` (35-71); consumer `apps/web/app/api/cron/streams/send-link-clicked-webhooks/route.ts` (per trace_path, hop-1 caller of `sendWebhooks`).
**Signature:** singleton `clickWebhookWorkspaces.{add,remove,has}(workspaceId)` over key `linkClickedWebhookWorkspaces`; `syncWorkspaceWebhookStatus(workspaceId): Promise<void>`.
**Data Shape:** one global Redis SET of workspace IDs that have ≥1 active (`disabledAt: null`) webhook subscribed to `link.clicked`. Plan-gated: only workspaces whose plan is NOT in `["free","pro"]` count.

### Decisive source
```ts
// syncWorkspaceWebhookStatus — recompute membership from source of truth
const activeWebhooks = await prisma.webhook.findMany({
  where: { projectId: workspaceId, disabledAt: null,
           project: { plan: { notIn: ["free", "pro"] } } },
  select: { triggers: true },
});
await prisma.project.update({
  where: { id: workspaceId },
  data: { webhookEnabled: activeWebhooks.length > 0 },   // DB flag mirrors
});
const linkClickWebhooks = activeWebhooks.filter((webhook) =>
  (webhook.triggers as WebhookTrigger[])?.includes(LINK_CLICK_WEBHOOK_TRIGGER));
if (linkClickWebhooks.length > 0) {
  await clickWebhookWorkspaces.add(workspaceId);
} else {
  await clickWebhookWorkspaces.remove(workspaceId);      // removal is explicit, not TTL
}
```

**Flow:** any webhook create/disable/failure-disable calls `syncWorkspaceWebhookStatus` → the workspace's membership in the click set is recomputed from Prisma (active + paid-plan + trigger-subscribed) and the `webhookEnabled` project flag is mirrored → the click pipeline's stream worker checks set membership (`has`) BEFORE doing any per-workspace DB reads.
**Invariant:** the set is a DERIVED index — it must be maintained on every mutation path that changes activity/plan/trigger state, because nothing expires it (no TTL). Removal is explicit. The mirror has two consumers reading DIFFERENT flags: `sendWorkspaceWebhook` gates on the `project.webhookEnabled` column; the click stream gates on the Redis set. Free/pro plans are excluded at the query level, so the set can never contain them.
**Probe:** no direct upstream unit test (coverage caveat — consumer-grounded check only). Deterministic probe: after `syncWorkspaceWebhookStatus`, a workspace with zero active click webhooks must be absent from the set (`sismember == 0`) and `project.webhookEnabled === false`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "syncWorkspaceWebhookStatus clickWebhookWorkspaces linkClickedWebhookWorkspaces", limit: 10 });
```

## Verdict
Adopt: derived Redis set as a hot-path eligibility filter for expensive event fan-out, recomputed from source-of-truth on every mutation, with an explicit remove branch. Adapt the eligibility predicate (plan gating) to your tiers; adapt storage to any shared set/hash structure. Omit the dual-flag mirroring if you have only one consumer.
