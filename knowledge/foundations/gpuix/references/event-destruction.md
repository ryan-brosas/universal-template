# Can queued native events invoke a destroyed element's callback?

Source: [remorses/gpuix](https://github.com/remorses/gpuix) at `a24b4a42eb516c7b940eb8d34ecebb077df623bd`, Apache-2.0. Paths below are relative to that checkout unless marked Heddlework. Historical evidence, not a live-runtime guarantee.

## Question and traced ownership

Does destruction cancel native callbacks, or suppress their eventual JS delivery?

- `packages/react/src/reconciler/host-config.ts:91-101,271-281,299-315,467-473`: `syncEventListeners` stores JS handlers and sends native listener flags. Deletion calls `destroyElement`; `resetAfterCommit` flushes mutations. Removing text must destroy it directly because React's `detachDeletedInstance` is host-component-only.
- `packages/react/src/reconciler/batch-renderer.ts:35-46,67-82`: `wrapWithBatching.destroyElement` only queues destruction and returns an empty list. After `inner.applyBatch` succeeds, `flushMutations` deletes every returned ID's handler map and clears the queue. Cleanup is not complete at the call that merely enqueues deletion.
- `packages/native/src/retained_tree.rs:242-273`: `destroy_element` unlinks the parent, recursively removes nodes, clears a deleted root and invalidates the parent chain; it returns all removed IDs. It does not own the JS closures.
- `packages/native/src/renderer.rs:4347-4368,4977-4996,794-800`: native click closures capture an ID and shared event emitter. `emit_event_full` constructs a payload without checking retained-tree membership. Production delivery calls the shared ThreadsafeFunction in NonBlocking mode. Node deletion does not cancel this queue or individually destroy this shared bridge.
- `packages/react/src/reconciler/event-registry.ts:9-26,33-56,82-87`: `handleGpuixEvent` looks up the currently attached renderer's container, then element ID and event type. A missing map suppresses invocation; it is not a native queue purge. Only the owner may detach a root.
- `packages/react/src/reconciler/reconciler.ts:58-75,104-115`: element allocation persists per renderer across roots; window-key payloads have a separate increasing root ID. Synchronous unmount and owner-checked detachment protect replacement roots. These safeguards assume allocator-managed IDs, not arbitrary low-level ID reuse.

## Invariants, counterevidence and failure boundary

After a successful deletion batch returns its IDs and JS cleanup runs, an old payload may reach the JS dispatcher but cannot find that element's handler. Root detachment similarly suppresses dispatch. This does not establish cancellation of an already executing callback, or safety before the deletion commit finishes. Events for a still-live ID resolve its current handler, not a captured historical JS handler.

Important exception: `renderer.rs:1193-1200` mutates through `apply_batch_to_tree`, then calls fallible `request_invalidate` before returning destroyed IDs. `renderer.rs:802-811,884-900` can fail when the UI command channel is absent/closed. Thus a post-mutation invalidation error can prevent JS handler cleanup even though native nodes were removed. `batch-renderer.ts:70-80` preserves the queue on a thrown call, not a destruction receipt. Retrying a destruction-only batch cannot recover IDs already removed. Do not elevate the batch comment about preventing desynchronization into a production transaction guarantee.

`renderer.rs:5289-5364` validates/normalizes before mutation inside the tree helper. That atomicity is narrower than the public N-API operation including repaint notification.

## Direct tests and bounded execution

Inspected `packages/react/src/__tests__/mutation-lifecycle.test.tsx:60-208`: isolated live roots, stale old-root element delivery after remount, retained text/subtree reclamation, rejecting a second owner and permitting replacement. These are native-renderer-gated tests; the stale payload is manually fed to `handleGpuixEvent`, not transported through a real TSFN race.

Inspected `packages/native/src/retained_tree.rs:564-591`: returned descendant IDs, parent unlink/revision and root clearing. `renderer.rs:5709-5733`, `a_malformed_style_applies_nothing_at_all`, proves tree-helper rejection leaves the tree/styles unchanged, not post-mutation invalidation recovery.

A setup-free Bun probe imported the actual event-registry and batch-renderer TS modules with an injected renderer. Passed assertions: handlers remain before flush; returned parent/child IDs both clear; late delivery after successful cleanup is ignored; a throwing applyBatch leaves a callable handler; detaching its owner suppresses delivery. The injected error represents a boundary, not execution of Rust or a native event queue. No upstream suite, native window or dependency setup ran.

## Heddlework comparison and disposition

Heddlework `src/ui/browser-host.tsx:39-73` keys native browser instances by tab/generation and routes tagged events to the service. `src/browser/service.ts:178-229,337-343` rejects missing tabs, stale generations and disposed services. Those application identities must survive even if renderer-ID cleanup fails. `src/workbench/plugins.ts:18-27,47-65` attaches listener/transport/controller inverses to plugin lifecycles rather than renderer lifetime.

`tests/browser-service.test.ts:97-134` directly tests old profile generations and service recreation. The whole module passed locally: 12 tests, 73 assertions, exit 0. This proves service behavior with its test filesystem harness, not native callback release or compositor behavior.

**Disposition: ADAPT.** Preserve renderer-scoped handler lookup plus non-reused identities, but retain Heddlework's service generation/disposal guards; successful native deletion receipts are not guaranteed when repaint notification fails. No application changes were made.

## Scope and next question

One event-routing/deletion seam; no claim about exact GPUI frame closure-drop timing or TSFN shutdown. Direct source navigation only; graph checks not applicable. Next: when does custom-element destruction run after retained-tree deletion, and does test teardown prove production teardown? See [native cleanup timing](native-cleanup-timing.md).
