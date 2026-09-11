<!-- capsule-v2 -->
# Lifecycles provider — how do before*/after* hook phases exchange arbitrary per-subscriber state without globals?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** What is the state-channel contract between a `beforeCreate` subscriber and its own `afterCreate` invocation, and how are subscribers safely removable?

## Lifecycle registry seam
**Path/Symbol:** `packages/core/database/src/lifecycles/index.ts:createLifecyclesProvider` (27–107; file is parse-partial at line 8 only — a type re-export, verified by direct read).
**Signature:** `run(action: Action, uid: string, properties: { params?, result? }, states?: States): Promise<States>` where `States = Map<Subscriber, State>`.
**Data Shape:** Subscriber = function `(event) => void` **or** object `{ [action]?: (event) => void, models?: string[] }`; `Event = { action, model, state, ...properties }`.

### Decisive source
```ts
async run(action, uid, properties, states = new Map()) {
  if (isLifecycleHooksDisabled) return states;
  for (let i = 0; i < subscribers.length; i += 1) {
    const subscriber = subscribers[i];
    if (typeof subscriber === 'function') {
      const state = states.get(subscriber) || {};
      const event = this.createEvent(action, uid, properties, state);
      await subscriber(event);
      if (event.state) { states.set(subscriber, event.state || state); }
      continue;
    }
    const hasAction = action in subscriber;
    const hasModel = !subscriber.models || subscriber.models.includes(uid);
    if (hasAction && hasModel) { ...same state threading... }
  }
  return states;
}
```

**Flow:** two built-in subscribers seed the list (`timestampsLifecyclesSubscriber`, `modelsLifecyclesSubscriber`) → `subscribe()` validates then appends and returns an unsubscribe closure (`() => subscribers.splice(indexOf, 1)`) → each mutation calls `run('before*', ...)` capturing the returned Map → business logic → `run('after*', ..., states)` re-invokes only matching subscribers with their previous state.
**Invariant:** State is keyed by *subscriber identity*, so one bad subscriber cannot leak into another's state; `disable()/enable()` gates all hooks (used for internal operations like migrations); object subscribers filter by both action name and optional `models` uid list.
**Probe:** `packages/core/database/src/__tests__/lifecycles.test.ts` — "store state" asserts `stateBefore.get(subscriber)` equals the state set inside the subscriber; "use shared state" asserts the exact state object reaches `afterCreate`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "lifecycles run subscribe return value state", limit: 15 });
```
Executed during pass 1: 528 total matches led by `lifecycles.subscribe` (36–45), `lifecycles.run` (76–105), `createLifecyclesProvider` (27–107).

## Verdict
Adopt the Map-keyed-by-subscriber state channel and unsubscribe-closure pattern verbatim — it is host-independent. Adapt the built-in subscriber seeding (timestamps/models) to your domain events. Omit Strapi's metadata lookup in `createEvent` (`db.metadata.get(uid)`) unless you port metadata too. Coverage caveat honored: parse-partial range 8-8 was read directly before citing this file.
