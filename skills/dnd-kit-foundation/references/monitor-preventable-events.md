<!-- capsule-v2 -->
# Monitor & preventable events — typed event map with closure-backed vetoes

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which events exist, which are cancelable, and why is defaultPrevented a getter over a closure?

## DragDropMonitor + event map
**Path/Symbol:** `packages/abstract/src/core/manager/events.ts:30-253`.
**Signature:** six events — `collision`, `beforedragstart`, `dragstart`, `dragmove`, `dragover`, `dragend`; all except `dragstart` (hard `cancelable:false`) are wrapped by `defaultPreventable(event, cancelable=true)`; handlers receive `(event, manager)`.
**Data Shape:** `Monitor` = `Map<name, Set<handler>>` with copy-on-add (`new Set(registry.get(name))` then set back) so add/remove during dispatch never mutates the in-flight iteration; dispatch passes `[event, manager]`.

### Decisive source
```ts
export function defaultPreventable<T>(event: T, cancelable = true): Preventable<T> {
  let defaultPrevented = false;
  return {
    ...event,
    cancelable,
    get defaultPrevented() { return defaultPrevented; },
    preventDefault() {
      if (!cancelable) return;      // dragstart ignores veto attempts entirely
      defaultPrevented = true;
    },
  };
}
```

**Flow:** emitters construct the plain payload → wrap via defaultPreventable → monitor.dispatch synchronously walks listeners → each consumer decides to call preventDefault() → AFTER dispatch the emitter reads `event.defaultPrevented` and branches (actions.move skips the microtask apply; CollisionNotifier skips target change; move/swap helpers return unchanged items + re-prevent). dragend uniquely carries a `suspend()` factory letting async listeners (drop animations) delay teardown.
**Invariant:** the closure getter means prevention state can NEVER be spoofed by spreading or JSON-cloning the event object — porting it as a plain mutable property reintroduces accidental un-prevent; handler sets are copied on mutation for re-entrancy safety (a listener may subscribe another).
**Probe:** veto semantics pinned across suites (move.test.ts asserts `event.defaultPrevented === true` on no-op paths :141-163; optimistic plugin checks it before applying); monitor lifecycle exercised by every kernel test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "defaultPreventable", name_pattern: "^DragDropMonitor$", limit: 10 });
```

## Verdict
Adopt the closure-getter preventable and copy-on-write listener registry verbatim; adapt the event vocabulary to your domain keeping the veto-after-dispatch read pattern; omit suspend() only if teardown is fully synchronous.
