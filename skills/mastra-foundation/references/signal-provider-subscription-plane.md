<!-- capsule-v2 -->
# signal-provider subscription plane — how does an external-event-to-agent-thread bridge track subscriptions, poll safely, and route webhooks?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** What is the reusable contract for a provider class that monitors an external source (GitHub PRs, Slack channels) and pushes notification signals into agent threads — subscription registry shape, polling guard, and lifecycle?

## Triple-index in-memory registry + overlap-guarded poll loop
**Path/Symbol:** `packages/core/src/signals/signal-provider.ts` : `SignalProvider` (:105-481) — `subscribe` (:225-267), `unsubscribe` (:270-291), `getSubscriptionsForResource` (:317-322), `unsubscribeAll` (:343-351), `startPolling` (:382-405), `stopPolling` (:408-413), `stop` (:439-445), `notify` (:454-468), key builders (#subscriptionKey/#threadKey :472-478).
**Signature:** abstract `SignalProvider<TId extends string>` with `abstract readonly id: TId`, optional `readonly pollInterval?: number`, optional `poll?(subscriptions: SignalSubscription[]): Promise<void>`, optional `handleWebhook?(request): Promise<{status?, body?}>`; subclass hooks `getInputProcessors?/getOutputProcessors?/getTools?`.
**Data Shape:** `SignalSubscription = { id: UUID; providerId; threadId; resourceId; externalResourceId (e.g. "github:owner/repo#123"); subscribedAt: Date; metadata }`. THREE parallel indexes over one canonical Map keyed `` `${resourceId}:${threadId}:${externalResourceId}` ``: by-resource (`externalResourceId → Set<key>`), by-thread (`${resourceId}:${threadId} → Set<key>`), plus the primary map.

### Decisive source
```typescript
// Duplicate subscribe MERGES metadata and returns the existing row — idempotent:
const existing = this.#subscriptions.get(key);
if (existing) { existing.metadata = { ...existing.metadata, ...metadata }; return existing; }

// Poll loop: re-entrancy guard + empty skip + timer.unref() so the process
// can exit while polling is armed:
this.#pollTimer = setInterval(() => {
  if (this.#isPollRunning) return;              // never overlap poll cycles
  const subscriptions = this.getSubscriptions();
  if (subscriptions.length === 0) return;
  this.#isPollRunning = true;
  void Promise.resolve(this.poll!(subscriptions))
    .catch(error => { console.warn(`[${this.id}] poll failed:`, error); })  // log, never throw
    .finally(() => { this.#isPollRunning = false; });
}, interval);
this.#pollTimer.unref?.();
```

**Flow:** Agent constructor calls `connect(agent)` (idempotency probe via `isConnected` for forked agents) → framework auto-starts polling when `pollInterval > 0 && poll defined` → each cycle hands a SNAPSHOT of subscriptions to `poll()`, which calls `notify(input, target)` → `agent.sendNotificationSignal(..., { resourceId, threadId, ifIdle? })` (throws loudly if no agent connected). Webhook providers instead implement `handleWebhook` after their own verification. `stop()` = stopPolling + clear all three indexes.
**Invariant:** Unsubscribe cleans up ALL indexes and deletes empty index sets (no leak); unsubscribe returns boolean, `unsubscribeAll` counts removals; poll errors are contained (warn + continue) — one bad cycle must never kill the interval; the timer must not hold the process open.
**Probe:** `packages/core/src/signals/signal-provider.test.ts` (574L): duplicate-subscribe metadata merge (:102), index cleanup on unsubscribe (:161), `notify throws when no agent is connected` (:211), polling guards: `does not start polling when pollInterval is not set/0` (:248/:256), `skips poll when no subscriptions` (:276).
**Coverage caveat:** registry is in-memory per provider instance (not durable) — multi-process deployments need the task/webhook provider twins (`task-signal-provider.ts`, `webhook-signal-provider.ts`) as reference instances.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "SignalProvider subscribe startPolling handleWebhook notify", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-index registry with merge-on-duplicate subscribe, the isPollRunning+unref poll pattern, and error-contained polling. Adapt key grammar and the `ifIdle` delivery options to your agent runtime. Omit the processor/tool hook surface if your providers only push notifications. Porters who let poll cycles overlap double-send notifications under slow upstreams; who forget unref leak idle timers into serverless lifetimes.
