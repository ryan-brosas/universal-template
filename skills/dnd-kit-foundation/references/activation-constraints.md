<!-- capsule-v2 -->
# Activation constraints — delay/distance gating without a drag state machine

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does "press 250ms OR move 5px" become composable, cancelable logic independent of any DOM framework?

## ActivationController + constraint classes
**Path/Symbol:** `packages/abstract/src/core/sensors/activation.ts:1-76` (`ActivationController`, `ActivationConstraint`); implementations `packages/dom/src/core/sensors/pointer/DelayConstraint.ts` + `DistanceConstraint.ts`.
**Signature:** `controller.onEvent(event)` fans to constraints; `constraint.onEvent(event)` decides; either side calls `activate(event)` (idempotent via `activated` flag) or `abort()`; controller is an `AbortController` subclass so sensors get signal semantics for free.
**Data Shape:** `constraints?: ActivationConstraint<E>[]` — empty/undefined means activate on FIRST event; DelayConstraint owns `#timeout`+`#coordinates`; DistanceConstraint owns `#coordinates`.

### Decisive source
```ts
// activation.ts
onEvent(event: E) {
  if (this.activated) return;
  if (this.constraints?.length) {
    for (const constraint of this.constraints) constraint.onEvent(event);
  } else {
    this.activate(event);            // no constraints = immediate activation
  }
}
abort(event?: E) {
  this.activated = false;            // reset BEFORE super.abort()
  super.abort(event);
}

// DelayConstraint.ts
case 'pointermove':
  if (!this.#coordinates) return;
  const delta = { x: x - this.#coordinates.x, y: y - this.#coordinates.y };
  if (exceedsDistance(delta, this.options.tolerance)) this.abort();  // wiggle cancels the timer
```

**Flow:** pointerdown → sensor creates controller with constraints, wires each constraint's abort-listener → every pointermove/up feeds `onEvent` → DelayConstraint arms a timer on down and kills it if movement exceeds tolerance or pointer lifts; DistanceConstraint activates when delta exceeds its value UNLESS an optional tolerance was exceeded first. Constraint `abort()` runs from BOTH directions: user input and `controller.signal` 'abort' events — so Escape keys, pointercancel, and competing drags all funnel through one path.
**Invariant:** `activate` fires at most once per controller; abort() must clear `activated` BEFORE dispatching super.abort() so listeners observe consistent state; tolerance semantics come from `exceedsDistance`: number = Euclidean magnitude, `{x,y}` object = AND over axes (`dx > t.x && dy > t.y`) — porting it as OR breaks slow-diagonal activation.
**Probe:** `packages/dom/tests/pointer-sensor.test.ts:20-81` (activate after delay; abort before elapse in two timings; pointerup cancels); live run of `exceedsDistance({x:3,y:4},5)=false / 4.9=true` and axis-AND matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "ActivationController", name_pattern: "^ActivationController$", limit: 10 });
```

## Verdict
Adopt the controller/constraint split and both constraint classes wholesale (they are host-independent apart from `getEventCoordinates`); adapt PointerSensor's defaults table (:44-87): handle-drags need NO constraints, touch gets Delay(250,tol 5), text inputs Delay(200, tol 0), mouse Delay(200,tol 10)+Distance(5); omit keyboard/touch special cases at your peril — they exist because of real mobile/text-selection behavior.
