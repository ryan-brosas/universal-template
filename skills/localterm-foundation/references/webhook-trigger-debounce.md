<!-- capsule-v2 -->
# Webhook trigger debounce — how does an external HTTP signal become exactly one automation run?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you coalesce duplicate webhook deliveries (CI retries, LB double-fires) into a single run without queueing stale fires?

## Stateless per-automation trailing debounce with fire-time re-validation
**Path/Symbol:** `packages/server/src/webhook-trigger-manager.ts:WebhookTriggerManager` (:31–69).
**Signature:** `trigger(automation: Automation): void`; constructor options `{ debounceMs, isRunInFlight(id), getAutomation(id) }`.
**Data Shape:** `debounceTimers: Map<automationId, NodeJS.Timeout>`; every timer `.unref()`-ed so pending debounces never hold the daemon alive; no per-automation state beyond the timer — the store IS the registry.

### Decisive source
```ts
trigger(automation: Automation): void {
    if (this.disposed) return;
    if (this.options.isRunInFlight(automation.id)) return;
    const existing = this.debounceTimers.get(automation.id);
    if (existing !== undefined) clearTimeout(existing);
    const timer = setTimeout(() => {
      this.debounceTimers.delete(automation.id);
      this.fire(automation.id);
    }, this.options.debounceMs);
```

**Flow:** POST `/api/webhooks/:id` → route resolves id→automation via `automationStore.getByWebhookId` and returns 404/409 for unknown/inactive ids, else 202 `{accepted:true}` ALWAYS (a CI retry loop must never amplify) → `trigger()` drops silently while a run is in-flight, else clears + rearms the trailing timer → on expiry `fire()` re-checks disposed, in-flight, then **re-reads live state via getAutomation** and validates enabled ∧ lifecycle==="active" ∧ trigger.kind still "webhook" before emitting `due`.
**Invariant:** The automation snapshot captured at POST time is NEVER trusted at fire time — an edit during the debounce window (disabled, limit reached, switched to schedule) wins because `getAutomation` is consulted inside `fire()`. A dropped in-flight POST does not queue: the next POST after settle re-arms.
**Probe:** `packages/server/tests/webhook-trigger-manager.test.ts` (8 `it()` blocks pin: burst→one due :53, window reset per POST :64, in-flight drop :77, fire-time disabled skip :87, finished skip :97, no emit after dispose :107, independent automations don't interfere :116).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "WebhookTriggerManager trigger debounce", limit: 10 });
```

## Verdict
Adopt the stateless shape (route does id lookup, manager holds only timers), the always-202 route posture, and fire-time re-validation; adapt debounceMs to your delivery profile (localterm: 500ms); omit Discord-style webhook-token auth details (route-level concern). Direct tests cover all 8 behaviors with fake timers.
