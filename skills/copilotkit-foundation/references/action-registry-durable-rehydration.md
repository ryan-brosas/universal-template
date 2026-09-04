<!-- capsule-v2 -->
# action-registry-durable-rehydration

## Source
- Repo: `copilotkit`
- Path: `packages/channels-core/src/action-registry.ts`
- Symbol: `ActionRegistry` / `persistMessageReaction` / `resolveMessageReaction` / `dispatch`
- Lines: 50-134 (registry fields + reaction plane), 349-365 (durable put w/ retention), 460-497 (dispatch)
- Commit: `e9387e04835545c45744b791aee7c9c03520be31` (verified byte-exact at working tree HEAD)
- Graph Node: `ext-copilotkit.packages.channels-core.src.action-registry.ActionRegistry`

## Signature & Data Shape
```typescript
export class ActionRegistry {
  constructor(opts: { store: ActionStore; retentionMs?: number });
  registerMessageReaction(messageId: string, handler: MessageReactionHandler): void;
  // Durable half of <Message onReaction>: {component, props} snapshot keyed by messageId
  persistMessageReaction(
    messageId: string,
    snap: { component: string; props: Record<string, unknown>;
            conversationKey: string; platform?: string },
  ): Promise<void>;                       // -> store.put(reactionKey(messageId), {...}) — NO ttl
  async resolveMessageReaction(messageId: string): Promise<MessageHandler | undefined>;
  async dispatch(id: string, ctx: InteractionContext): Promise<unknown>; // returns element `value`
}
// ActionStore (action-store.ts:44): put(id, snap, ttlMs?) / get / consume / delete
```

## Decisive Source Excerpt
```typescript
  // Cache the handler AND the element's `value` per minted id. The value is
  // needed to resolve HITL `awaitChoice` waiters on platforms whose callback
  // payload can't carry it (e.g. Telegram's 64-byte callback_data only holds
  // the action id), where `evt.value` arrives undefined.
  private hot = new Map<
    string,
    { handler: ClickHandler; value: unknown; continuation?: true }
  >();
  ...
  async persistMessageReaction(
    messageId: string,
    snap: {
      component: string;
      props: Record<string, unknown>;
      conversationKey: string;
      platform?: string;
    },
  ): Promise<void> {
    await this.store.put(reactionKey(messageId), {
      component: snap.component,
      props: snap.props,
      path: [],
      conversationKey: snap.conversationKey,
      platform: snap.platform,
    });
  }
```
Retention wiring (:349-365, inside the event-prop binding walk):
```typescript
          await this.store.put(id, { ...snapshot... }, continuation ? this.retentionMs : undefined);
```
Cold dispatch degradation (:460-497): hot miss → `store.get(id)` → snapshot or **ActionExpiredError**;
unregistered component name → **ActionExpiredError**; handler re-found by `locator`/`path`, value from
`snap.actionValue`/`pluckValue`; returned `value === undefined ? ctx.action.value : value`.

## Flow
1. Dual-tier storage: in-memory `hot` map for same-process dispatch; persistent `ActionStore`
   snapshots (`{component, props, path, locator?, actionValue?, conversationKey, platform}`) for
   cross-restart recovery.
2. Mint unique action ids during `bindTree`; record handler AND element `value` in `hot` so HITL
   `awaitChoice` resolves on payload-limited platforms (Telegram 64-byte `callback_data` carries
   only the id).
3. `<Message onReaction>` handlers are pulled OFF the bound IR (`bindRenderable`) and persisted by
   `persistMessageReaction` as a `{component, props}` snapshot under `reactionKey(messageId)` —
   deliberately WITHOUT a TTL.
4. After restart, `resolveMessageReaction` re-resolves: hot map first, then `store.get(reactionKey)`
   → re-render the registered component → `takeMessageReaction(root)` re-plucks the handler.
   Inline/anonymous components degrade to `undefined` (closure can't be re-derived).
5. `retentionMs` applies ONLY to continuation snapshots (`continuation ? this.retentionMs :
   undefined` :364); the test pins expiry via `claimContinuation` rejecting `ActionExpiredError`.

## Invariant
Interactive callbacks survive restarts through named-component snapshots + registry re-render; the
element `value` must be cached server-side because small-payload platforms cannot carry it.
`retentionMs` gates CONTINUATIONS only — reactions and plain onClick snapshots never expire via this
path; a cold-cache dispatch with a missing snapshot or unregistered component throws
`ActionExpiredError` (intended degradation, not a bug).

## Direct-Test Probe
- File: `packages/channels-core/src/action-registry.test.ts`
- Suite: `describe("ActionRegistry")` :40 — key cases: cold-path re-render after `clearHotCache()`
  :57; restart survival via shared store :79; `ActionExpiredError` on absent snapshot :104; NO-registration
  degradation :146; "expires with the action retention window" :332 (`vi.advanceTimersByTime(101)`
  then `claimContinuation` rejects).
```bash
grep -n 'describe("ActionRegistry"' packages/channels-core/src/action-registry.test.ts   # -> 40
grep -c 'saveReaction' packages/channels-core/src/action-registry.ts                     # -> 0 (no such API)
```

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"ActionRegistry persistMessageReaction awaitChoice ActionStore","limit":3,"detail":"compact"}'
# rank-1: ...action-registry.ActionRegistry.persistMessageReaction 96-112
```

## Verdict
Adopt the dual-tier hot/durable action registry, server-side element-value caching, and the
reactionKey snapshot protocol. Port the retention semantics EXACTLY: TTL on continuations only,
never on click/reaction snapshots.
