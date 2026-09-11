<!-- capsule-v2 -->
# React binding — stable instances, tracked deep signals, and the rendering promise bridge

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does a signals-based kernel stay reactive under React without re-creating entities on every render, and how does React "rendering" become an awaitable for the FSM gate?

## DragDropProvider / useInstance / Renderer
**Path/Symbol:** `packages/react/src/core/context/DragDropProvider.tsx:47-168`, `core/hooks/useInstance.ts:15-28`, `core/context/renderer.ts:18-55`, `core/draggable/useDraggable.ts:21-107`.
**Signature:** `useStableInstance(create)` — ref-created manager destroyed in `useInsertionEffect` cleanup (unmount-only, empty deps); `trackRendering(callback)` wraps event handlers in `startTransition` and resolves a promise in a layout effect keyed on `[children, transitionCount]`.
**Data Shape:** props → `resolveCustomizable(input, defaultPreset)`; handler props read through `useLatest` refs so listeners never need re-binding.

### Decisive source
```ts
// useInstance — one entity per component instance, manager swap handled
const [instance] = useState<T>(() => initializer(manager));
if (instance.manager !== manager) {
  instance.manager = manager;            // reactive accessor: re-registers
}
useIsomorphicLayoutEffect(instance.register, [manager, instance]);

// renderer.ts — the bridge that makes status promotion await the DOM
trackRendering(callback) {
  if (!rendering.current) {
    rendering.current = new Promise<void>((resolve) => { resolver.current = resolve; });
  }
  startTransition(() => { callback(); setTransitionCount((c) => c + 1); });
}
useIsomorphicLayoutEffect(() => {
  resolver.current?.();
  rendering.current = null;
}, [children, transitionCount]);

// useDraggable — synchronous flag update exactly once: drop-animation end
function shouldUpdateSynchronously(key, oldValue, newValue) {
  if (key === 'isDragSource' && !newValue && oldValue) return true;
  return false;
}
```

**Flow:** Provider builds/owns the manager, installs monitor→prop bridges (dragover/move/end callbacks are wrapped in trackRendering so their state updates are awaited by `manager.renderer.rendering`), and syncs plugins/sensors/modifiers via `deepEqual`-guarded effects. Hooks create the entity ONCE (`useState` initializer), mutate its reactive fields on prop changes (`useOnValueChange`), register via layout effect, and expose a `useDeepSignal`-tracked view so signal mutations trigger re-renders. The ref-callback refuses to detach the element while it is connected mid-drag (prevents sortable reparenting from unregistering the source).
**Invariant:** entity construction must never depend on unstable prop identity; every user-facing event callback that mutates observable state runs inside trackRendering or the FSM's dragstart would race React's commit; the single synchronous-update carve-out exists because after the drop animation the stale `isDragSource=true` frame flashes otherwise.
**Probe:** no upstream React unit tests ship in-repo (binding coverage caveat); contracts pinned indirectly by abstract-level suites + stories apps; port with your own RTL test asserting provider unmount destroys the manager.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "DragDropProvider", name_pattern: "^DragDropProvider$", limit: 10 });
```

## Verdict
Adopt stable-instance + tracked-view separation and the transition-tracked rendering promise; adapt to Solid/Vue/Svelte equivalents following the same contract (the repo's sibling packages prove the port); omit useInsertionEffect timing only if you can guarantee no child renders before teardown.
