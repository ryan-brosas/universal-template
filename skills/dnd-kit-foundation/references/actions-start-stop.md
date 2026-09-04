<!-- capsule-v2 -->
# Actions: start/stop/move — how do listeners veto a move, and what does dragend's suspend() mean?

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How are move-application and operation-teardown ordered relative to event listeners so preventDefault actually cancels and cleanup never races the drop animation?

## DragActions contracts
**Path/Symbol:** `packages/abstract/src/core/manager/actions.ts` (`move` :172-219, `stop` :233-317, `setDropTarget` :52-75).
**Signature:** `move(args?: {by?, to?, event?, cancelable? = true, propagate? = true}): void`; `stop(args?: {event?, canceled? = false}): void`; `setDropTarget(id): Promise<boolean>`.
**Data Shape:** events are plain objects wrapped by `defaultPreventable()` (closure-backed `defaultPrevented` + gated `preventDefault`, events.ts:232-252); snapshots via `dragOperation.snapshot()` are untracked.

### Decisive source
```ts
// move(): dispatch first, apply coordinates in a MICROTASK
if (args.propagate ?? true) {
  this.manager.monitor.dispatch('dragmove', event);
}

queueMicrotask(() => {
  if (event.defaultPrevented) return;          // listener veto = no movement
  const coordinates = args.to ?? {
    x: dragOperation.position.current.x + (args.by?.x ?? 0),
    y: dragOperation.position.current.y + (args.by?.y ?? 0),
  };
  dragOperation.position.current = coordinates;
});

// stop(): suspend protocol + dropping-aware reset
const suspend = () => { /* resume/abort promise pair */ };
controller.abort();
dragOperation.canceled = args.canceled ?? false;
this.manager.monitor.dispatch('dragend', {...event, suspend});
if (promise) { promise.then(end).catch(() => dragOperation.reset()); } else { end(); }
// end(): after renderer tick → status=Dropped → if source.status==='dropping',
// an effect waits for source idle BEFORE reset() (else one more renderer tick)
```

**Flow:** move = guard(dragging+controller alive) → dispatch dragmove synchronously → microtask applies `to ?? current+by` unless prevented. stop = abort controller FIRST (kills in-flight start ticks) → dispatch dragend with suspend() factory → if a listener called suspend(), teardown waits on the returned promise (reject = immediate reset); otherwise end() sets Dropped after the renderer tick and defers `reset()` while the source is mid-drop-animation.
**Invariant:** position mutation happens strictly AFTER all dragmove listeners ran (same-microtask ordering), so a listener that reads `position.current` sees the pre-move value; `reset()` must not run while any source is 'dropping' or its animation reads torn state; setDropTarget resolves to `event.defaultPrevented` AFTER rendering, letting callers react to vetoes asynchronously.
**Probe:** `packages/abstract/tests/drag-event-order.test.ts` (ordering) + live kernel run: second `start()` during active drag throws "Cannot start a drag operation while another is active"; stop→idle verified after flush.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "DragActions", name_pattern: "^DragActions$", limit: 10 });
```

## Verdict
Adopt the dispatch-then-microtask-apply pattern and the suspend/resume/abort teardown triple; adapt the microtask to your scheduler if listeners can be async; omit the dropping-source wait only if you have no drop animation.
