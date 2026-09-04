<!-- capsule-v2 -->
# Drag status FSM — when is a drag officially "started" and why do pre-render moves vanish?

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** What are the exact states, and which state gates must a porter reproduce so events don't fire before the host has rendered?

## Status state machine
**Path/Symbol:** `packages/abstract/src/core/manager/status.ts:6-103` (`StatusValue`, `Status`); gated in `actions.ts:138-156`.
**Signature:** `enum StatusValue { Idle='idle', InitializationPending='initialization-pending', Initializing='initializing', Dragging='dragging', Dropped='dropped' }`; derived flags: `idle`, `initializing`, `initialized`, `dragging`, `dropped`.
**Data Shape:** single reactive accessor `value`; every boolean check is a `@derived` getter (computed-signal memoized per instance).

### Decisive source
```ts
// actions.ts start(), after beforedragstart was not prevented:
dragOperation.status.set(StatusValue.Initializing);
dragOperation.controller = controller;

this.manager.renderer.rendering.then(() => {
  if (controller.signal.aborted) return;
  const {status} = dragOperation;
  if (status.current !== StatusValue.Initializing) return;  // stale tick guard

  batch(() => {
    dragOperation.status.set(StatusValue.Dragging);
    this.manager.monitor.dispatch('dragstart', { ... });
  });
});

// status.ts
public get initialized(): boolean {
  const {value} = this;
  return value !== StatusValue.Idle && value !== StatusValue.InitializationPending;
}
```

**Flow:** Idle → (actions.start) InitializationPending → [beforedragstart not prevented] → Initializing → [renderer.rendering resolves AND still Initializing] → Dragging → (actions.stop; renderer tick) Dropped → reset → Idle. The renderer gate means `dragstart` NEVER precedes the host's commit; sensors' `move()` checks `status.dragging`, so pointer events landing during Initializing are silently dropped — that is the intended pre-activation dead zone, not a bug.
**Invariant:** exactly one transition per render tick (`current !== Initializing` guard); a canceled controller can never promote to Dragging; `initialized` deliberately INCLUDES Initializing (collision observer uses it to force updates early) but EXCLUDES InitializationPending.
**Probe:** `packages/abstract/tests/drag-event-order.test.ts:18-88` pins dragstart-before-dragover with the Feedback-plugin timing mimic; live run: sync status after `start()` = `initializing`, after renderer tick = `dragging`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Status StatusValue", name_pattern: "^Status$", limit: 10 });
```

## Verdict
Adopt the five-state vocabulary and the renderer-promise promotion gate verbatim; adapt "renderer" to your framework's post-commit hook (React: flushSync/layout effect boundary); omit InitializationPending if your activators are synchronous — but then audit every `initialized` consumer.
