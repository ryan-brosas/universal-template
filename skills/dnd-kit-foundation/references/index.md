<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# dnd-kit: headless drag-and-drop kernel

## Use this for
Use when building or porting pointer/touch/keyboard drag-and-drop systems: framework-agnostic drag state machines, sensor activation constraints (delay/distance), collision detection ladders, optimistic sortable reordering with reconciliation, auto-scroll intent locking, screen-reader announcement plumbing, or drop animation choreography. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./manager-kernel.md` — DragDropManager composition root and the modifier lifecycle effect.
- `./status-state-machine.md` — five-state drag status FSM and the renderer-gated start transition.
- `./actions-start-stop.md` — start/stop/move action contracts incl. the suspend protocol.
- `./entity-id-batching.md` — microtask-batched atomic id swaps for virtualized sorting.
- `./entity-registry.md` — copy-on-write reactive registry with effect-scoped cleanups.
- `./activation-constraints.md` — ActivationController + Delay/Distance constraint algebra.
- `./collision-observer-notifier.md` — shape-keyed recomputation and the disable-during-setDropTarget loop guard.
- `./monitor-preventable-events.md` — six-event typed map with closure-backed preventDefault vetoes.
- `./plugin-registry-dedupe.md` — first-position-wins dedupe, per-entity config, CorePlugin immortality.
- `./signals-toolkit.md` — @reactive/@derived decorators, ValueHistory, WeakStore primitives.
- `./geometry-primitives.md` — Shape contract, Rectangle algebra, exceedsDistance dialects.
- `./scheduling-listeners.md` — rAF-coalesced dedupe scheduler and leak-proof listener registry.
- `./frame-coordinate-traversal.md` — elementFromPoint iframe descent and frame-transform math.
- `./pointer-sensor-defaults.md` — per-input activation matrix + pointer-capture choreography.
- `./keyboard-drag-loop.md` — keyboard operation loop with auto-scroll suppression.
- `./native-drag-encoding.md` — zero-width case-escaped base64 dataTransfer payloads.
- `./droppable-shape-lifecycle.md` — eligibility-gated observation windows and PositionObserver machine.
- `./collision-algorithms-ladder.md` — detector value semantics and the pointer-first composition ladder.
- `./sortable-facade-pairing.md` — draggable+droppable pairing and WeakStore drag snapshots.
- `./sortable-transition-measure.md` — cancel-CSS-transitions-before-measure FLIP deltas.
- `./optimistic-sorting-reconciliation.md` — DOM-first reorder with snapshot-based abort ladder.
- `./move-swap-helpers.md` — ID-vs-sortable-index dual lookup and optimistic reconciliation.
- `./auto-scroll-intent-locking.md` — ScrollIntent unlock-only-on-repeat and first-match scrolling.
- `./a11y-live-region-tabindex.md` — batched attribute mutations and debounced announcements.
- `./style-injector-refcount.md` — refcounted cross-root style injection with prepend defense.
- `./cursor-style-plugin.md` — optional-dependency grabbing-cursor micro-plugin shape.
- `./feedback-rendering.md` — placeholder proxying, popover promotion, transform-capture race.
- `./drop-animation-choreography.md` — final-keyframe capture, size morphing, focus restore.
- `./react-binding-renderer.md` — stable instances, tracked deep signals, rendering promise bridge.
- `./axis-modifier-pinning.md` — declarative axis pinning via the descriptor configurator.

## Capsule map
- **Kernel composition** — `manager-kernel`: manager wires monitor→registry→actions→operation→collisionObserver; CollisionNotifier force-injected FIRST; source modifiers REPLACE manager modifiers per operation. `plugin-registry-dedupe`: first-position/last-options dedupe, per-entity descriptor-only config, CorePlugin immortality.
- **Drag FSM** — `status-state-machine`: Idle→InitializationPending→Initializing→Dragging→Dropped with renderer-gated promotion; `monitor-preventable-events`: closure-getter defaultPrevented, dragstart hard non-cancelable, suspend() on dragend.
- **Action contracts** — `actions-start-stop`: move applies coordinates in a queueMicrotask AFTER listeners run; stop abort-first, suspends via dragend, defers reset while source is 'dropping'.
- **Entity identity & registration** — `entity-id-batching`: static pendingIdChanges Map + one microtask flush for atomic swaps; `entity-registry`: peek-mutate-publish Maps, WeakMap effect ownership, ghost sweep, value-guarded unregister.
- **Reactive toolkit** — `signals-toolkit`: @reactive peek-equality setters, @derived per-instance computed, ValueHistory {current,initial,previous}, manager-keyed WeakStore.
- **Sensor input** — `activation-constraints`: ActivationController + Delay(tolerance wiggle-cancel)/Distance constraints; `pointer-sensor-defaults`: mouse-handle-immediate / touch-delay-250 / text-delay-200-tol-0 / mouse-delay+distance matrix, body pointer capture, window touchmove patch; `keyboard-drag-loop`: Space/Enter start, arrows pan via prevented scroll-by, Shift×5, AutoScroller suppression; `native-drag-encoding`: zero-width-wrapped uppercase runs over base64 for MIME-type payload survival.
- **Collision plane** — `collision-observer-notifier`: read-to-subscribe shapes, coordinate-equality skip, disable/re-enable window around setDropTarget; `collision-algorithms-ladder`: `{id,value=1/distance,type,priority}` contract, priority→type→value sort, pointerIntersection ?? shapeIntersection defaults; `droppable-shape-lifecycle`: eligibility-gated observation windows and the PositionObserver visibility machine.
- **Geometry** — `geometry-primitives`: Shape contract, Euclidean-vs-per-axis exceedsDistance dialects (AND semantics!), inverse-scale plumbing.
- **Scheduling & frames** — `scheduling-listeners`: dedupe-by-reference rAF scheduler with swap-first flush; `frame-coordinate-traversal`: shadow-root-aware elementFromPoint with iframe descent, scale+offset conversion at sensor boundaries.
- **Sortable UX** — `sortable-facade-pairing`: batched dual-entity setters, manager-scoped initial snapshots in a WeakStore, split disabled normalization; `sortable-transition-measure`: cancel transform transitions before measuring, reduced-motion zeroing, drag-gated shape clearing; `optimistic-sorting-reconciliation`: pre-await snapshot abort checks, DOM-first then batched index writes, canceled-drag rollback; `move-swap-helpers`: three-tier lookup (id → sortable-index fallback → projection reconcile) over arrays or grouped records.
- **Auto-scroll** — `auto-scroll-intent-locking`: directions unlock only when observed twice consecutively, first-match container scroll, 10ms interval loop.
- **Accessibility** — `a11y-live-region-tabindex`: needed-diff mutation sets flushed via one scheduled task, 500ms debounce only for dragover/dragmove, immediate-and-cancel for terminal events.
- **Style injection** — `style-injector-refcount`: global refcount registry, prepend-for-lowest-cascade with removal self-heal, adoptedStyleSheets for shadow roots; `cursor-style-plugin`: optional-dependency + composed-destroy reference plugin.
- **Feedback & animation** — `feedback-rendering`: capture raw transform BEFORE the dragging attribute's !important lands, nested-droppable proxying through clones, popover promotion; `drop-animation-choreography`: pause running transition → tween to slot with size-morph keyframes → finish paused → rAF-deferred focus restore.
- **Framework binding** — `react-binding-renderer`: useState-once entities + reactive field sync, useInsertionEffect-owned manager lifetime, trackRendering/startTransition promise bridging into the FSM gate.
- **Modifiers** — `axis-modifier-pinning`: pure fold-over-snapshot transforms, configurator-produced constants.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
dnd-kit monorepo (MIT), `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory project `ext-ui-dnd-kit` (4,952 nodes / 11,382 edges, FULL mode, generation 2026-08-23T11:11Z, zero parse_partial flags inside cited packages — flags confined to apps/docs+stories/templates markup).

## Full view (memory graph)
Revalidate `ext-ui-dnd-kit` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the reactive kernel contracts (status machine, id batching, constraint algebra, collision loop guards, optimistic reconciliation); adapt the DOM adapter specifics (popover promotion, iframe descent, frame transforms) to your host's element model; omit the framework binding packages beyond the captured React contract (`solid`, `vue`, `svelte`) and Storybook stories/templates — they consume the captured contracts.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`a11y-live-region-tabindex.md`](./a11y-live-region-tabindex.md)
- [`actions-start-stop.md`](./actions-start-stop.md)
- [`activation-constraints.md`](./activation-constraints.md)
- [`auto-scroll-intent-locking.md`](./auto-scroll-intent-locking.md)
- [`axis-modifier-pinning.md`](./axis-modifier-pinning.md)
- [`collision-algorithms-ladder.md`](./collision-algorithms-ladder.md)
- [`collision-observer-notifier.md`](./collision-observer-notifier.md)
- [`cursor-style-plugin.md`](./cursor-style-plugin.md)
- [`drop-animation-choreography.md`](./drop-animation-choreography.md)
- [`droppable-shape-lifecycle.md`](./droppable-shape-lifecycle.md)
- [`entity-id-batching.md`](./entity-id-batching.md)
- [`entity-registry.md`](./entity-registry.md)
- [`feedback-rendering.md`](./feedback-rendering.md)
- [`frame-coordinate-traversal.md`](./frame-coordinate-traversal.md)
- [`geometry-primitives.md`](./geometry-primitives.md)
- [`keyboard-drag-loop.md`](./keyboard-drag-loop.md)
- [`manager-kernel.md`](./manager-kernel.md)
- [`monitor-preventable-events.md`](./monitor-preventable-events.md)
- [`move-swap-helpers.md`](./move-swap-helpers.md)
- [`native-drag-encoding.md`](./native-drag-encoding.md)
- [`optimistic-sorting-reconciliation.md`](./optimistic-sorting-reconciliation.md)
- [`plugin-registry-dedupe.md`](./plugin-registry-dedupe.md)
- [`pointer-sensor-defaults.md`](./pointer-sensor-defaults.md)
- [`react-binding-renderer.md`](./react-binding-renderer.md)
- [`scheduling-listeners.md`](./scheduling-listeners.md)
- [`signals-toolkit.md`](./signals-toolkit.md)
- [`sortable-facade-pairing.md`](./sortable-facade-pairing.md)
- [`sortable-transition-measure.md`](./sortable-transition-measure.md)
- [`status-state-machine.md`](./status-state-machine.md)
- [`style-injector-refcount.md`](./style-injector-refcount.md)
